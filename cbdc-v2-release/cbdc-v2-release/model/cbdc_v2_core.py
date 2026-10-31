"""
cbdc_v2_core.py : shared simulation core for the v2 CBDC confirmation-time study.

Every notebook imports this file, so all designs and scenarios use one implementation
(v1 had a separate copy per notebook, which produced inconsistent baselines).

WHAT IS QUEUED AT EACH STAGE (Fabric pipeline, Section 3.2 of the paper)
  1. Endorsement: each of the c peers has its own FCFS queue (simpy.Resource, capacity 1) and executes
     one proposal at a time, Exp(mu_e). Default dispatch sends a transaction to a uniformly random
     subset of q alive peers and waits for all of them; hedged dispatch sends it to all alive peers
     and proceeds on the q-th response. Late copies are still executed (no cancellation).
  2. Ordering: endorsed transactions join the leader's buffer (simpy.Store). A block opens at its
     first transaction and is cut at B transactions or tau seconds after opening. Cut blocks queue
     FCFS for the replication server (simpy.Resource, capacity 1), service s0 + s1*N.
  3. Validation and commit: each replicated block is delivered to every alive peer; each peer has a
     separate FCFS commit queue (simpy.Resource, capacity 1), service (v0 + v1*N) * peer_slowdown.
     A transaction is confirmed when its own gateway peer commits its block.
  Endorsement and commit are separate resources on each peer (stated modelling assumption).

MEASUREMENT
  Warm-up `warmup` seconds, then transactions ARRIVING in [warmup, warmup + measure) are measured.
  The run continues until all measured transactions are confirmed (or a drain limit is reached,
  which flags instability). Replications use independent seeds; designs compared on the same
  replication index share arrival streams (common random numbers).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field, replace
from typing import Callable, Optional
import numpy as np
import simpy
from scipy import stats


# --------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------
@dataclass
class PipelineConfig:
    lam: float = 200.0            # mean offered load (TPS); scaled by load_profile if given
    c: int = 5                    # endorsing peers (one per institution)
    q: int = 3                    # endorsement threshold
    mu_e: float = 200.0           # per-peer endorsement rate (proposals/s)  [ILLUSTRATIVE]
    dispatch: str = "default"     # "default" (send to q, wait all) or "hedged" (send to all, first q)
    B: int = 10                   # max transactions per block
    tau: float = 2.0              # block timeout (s), from first transaction in block
    s0: float = 0.020             # replication cost per block (s)  [ILLUSTRATIVE]
    s1: float = 0.001             # replication cost per transaction (s)  [ILLUSTRATIVE]
    v0: float = 0.010             # commit cost per block (s)  [ILLUSTRATIVE]
    v1: float = 0.002             # commit cost per transaction (s)  [ILLUSTRATIVE]
    peer_slowdown: Optional[list] = None   # per-peer multiplier on commit time (heterogeneous banks)
    warmup: float = 300.0
    measure: float = 600.0
    drain_limit: float = 600.0    # extra time allowed for measured txns to finish
    seed: int = 0
    # time-varying load: function t -> multiplier on lam (for ramps and surges); None = constant
    load_profile: Optional[Callable[[float], float]] = None
    load_max_mult: float = 1.0    # upper bound of load_profile (for thinning)
    # failures: list of (time, list_of_peer_ids_to_fail, new_q or None). A failed peer loses its
    # queued and in-service endorsement requests and stops committing.
    failures: list = field(default_factory=list)
    detect_delay: float = 0.5     # s before a lost endorsement request is re-sent to a surviving peer
    reconnect_delay: float = 0.5  # s for a client whose gateway failed to reconnect to a surviving peer


# --------------------------------------------------------------------------------------------
# Pipeline model
# --------------------------------------------------------------------------------------------
class FabricPipeline:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.env = simpy.Environment()
        ss = np.random.SeedSequence(cfg.seed)
        a, e, g, d = ss.spawn(4)
        self.rng_arr = np.random.default_rng(a)     # arrivals (shared across designs: CRN)
        self.rng_end = np.random.default_rng(e)     # endorsement execution times and peer choice
        self.rng_gw = np.random.default_rng(g)      # gateway peer of each transaction
        self.rng_misc = np.random.default_rng(d)
        self.endorse_res = [simpy.Resource(self.env, capacity=1) for _ in range(cfg.c)]
        self.commit_res = [simpy.Resource(self.env, capacity=1) for _ in range(cfg.c)]
        self.alive = [True] * cfg.c
        self.active = [set() for _ in range(cfg.c)]   # running endorsement processes per peer
        self.q = cfg.q
        self.slow = cfg.peer_slowdown or [1.0] * cfg.c
        self.buffer = simpy.Store(self.env)
        self.road = simpy.Resource(self.env, capacity=1)
        self.records = []          # (arrival, endorsed, replicated, committed, gateway)
        self.n_measured = 0
        self.n_done_measured = 0
        self.block_sizes = []

    # ---------------- arrivals ----------------
    def generator(self):
        cfg, env = self.cfg, self.env
        lam_max = cfg.lam * (cfg.load_max_mult if cfg.load_profile else 1.0)
        end = cfg.warmup + cfg.measure
        while True:
            yield env.timeout(self.rng_arr.exponential(1.0 / lam_max))
            t = env.now
            if t >= end:
                return
            if cfg.load_profile is not None:          # thinning for time-varying rate
                if self.rng_arr.random() > cfg.load_profile(t) / cfg.load_max_mult:
                    continue
            rec = [t, None, None, None, None, None, None]   # arr, endorsed, replicated, committed, gateway, status, block
            if cfg.warmup <= t < end:
                self.n_measured += 1
            env.process(self.transaction(rec))

    # ---------------- stage 1: endorsement ----------------
    def _endorse_at(self, peer):
        """Returns True if the peer completed the proposal, False if the peer failed first."""
        try:
            with self.endorse_res[peer].request() as req:
                yield req
                yield self.env.timeout(self.rng_end.exponential(1.0 / self.cfg.mu_e))
            return self.alive[peer]
        except simpy.Interrupt:
            return False

    def _launch(self, peer):
        proc = self.env.process(self._endorse_at(peer))
        self.active[peer].add(proc)
        proc.callbacks.append(lambda _e, p=peer, pr=proc: self.active[p].discard(pr))
        return proc

    def transaction(self, rec):
        cfg, env = self.cfg, self.env
        used, ok = set(), 0
        while True:
            alive = [p for p in range(cfg.c) if self.alive[p] and p not in used]
            need = self.q - ok
            if len(alive) + 0 < need and cfg.dispatch == "default":
                rec[5] = "unendorsable"; self.records.append(rec); return
            if cfg.dispatch == "default":
                peers = list(self.rng_end.choice(alive, need, replace=False))
                used.update(peers)
                results = yield env.all_of([self._launch(p) for p in peers])
                ok += sum(1 for v in results.values() if v)
                if ok >= self.q:
                    break
            else:                                    # hedged: all alive peers not yet used
                if len(alive) == 0 and ok < self.q:
                    rec[5] = "unendorsable"; self.records.append(rec); return
                used.update(alive)
                done = env.event(); cnt = [ok, len(alive)]
                def cb(ev, cnt=cnt, done=done):
                    cnt[1] -= 1
                    if ev.value:
                        cnt[0] += 1
                    if not done.triggered and (cnt[0] >= self.q or cnt[1] == 0):
                        done.succeed()
                for p in alive:
                    self._launch(p).callbacks.append(cb)
                yield done
                ok = cnt[0]
                if ok >= self.q:
                    break
            yield env.timeout(cfg.detect_delay)      # some copies were lost to a failure: re-send
        rec[1] = env.now
        rec[4] = int(self.rng_gw.choice([p for p in range(cfg.c) if self.alive[p]]))
        self.records.append(rec)
        yield self.buffer.put(rec)

    # ---------------- stage 2: ordering (formation + replication) ----------------
    def block_cutter(self):
        cfg, env = self.cfg, self.env
        while True:
            first = yield self.buffer.get()
            block = [first]; deadline = env.now + cfg.tau
            while len(block) < cfg.B:
                get = self.buffer.get()
                timer = env.timeout(max(deadline - env.now, 0.0))
                res = yield get | timer
                if get in res:
                    block.append(res[get])
                else:
                    get.cancel()
                    break
            self.block_sizes.append(len(block))
            env.process(self.replicate(block))

    def replicate(self, block):
        cfg, env = self.cfg, self.env
        N = len(block)
        with self.road.request() as req:
            yield req
            yield env.timeout(cfg.s0 + cfg.s1 * N)
        t = env.now
        commits = {}                            # peer -> commit time of this block
        for rec in block:
            rec[2] = t; rec[6] = commits
        for p in range(cfg.c):                  # deliver to every alive peer
            if self.alive[p]:
                env.process(self.commit(p, block))

    # ---------------- stage 3: validation and commit ----------------
    def commit(self, peer, block):
        cfg, env = self.cfg, self.env
        N = len(block)
        with self.commit_res[peer].request() as req:
            yield req
            yield env.timeout((cfg.v0 + cfg.v1 * N) * self.slow[peer])
        if not self.alive[peer]:
            return                               # peer failed before finishing this block
        t = env.now
        block[0][6][peer] = t
        end = cfg.warmup + cfg.measure
        for rec in block:
            if rec[4] == peer and rec[3] is None:
                rec[3] = t
                if cfg.warmup <= rec[0] < end:
                    self.n_done_measured += 1

    # ---------------- failures ----------------
    def failure_process(self):
        cfg, env = self.cfg, self.env
        end = cfg.warmup + cfg.measure
        for (t, peers, new_q) in sorted(cfg.failures, key=lambda x: x[0]):
            yield env.timeout(max(t - env.now, 0.0))
            for p in peers:
                self.alive[p] = False
                for proc in list(self.active[p]):
                    if proc.is_alive:
                        proc.interrupt("peer failure")
            if new_q is not None:
                self.q = new_q
            env.process(self._reconnect_clients(set(peers)))

    def _reconnect_clients(self, failed):
        """Clients whose gateway failed reconnect to a surviving peer after reconnect_delay; if that peer
        has already committed the block, confirmation is reported on reconnection."""
        cfg, env = self.cfg, self.env
        yield env.timeout(cfg.reconnect_delay)
        alive = [p for p in range(cfg.c) if self.alive[p]]
        end = cfg.warmup + cfg.measure
        for rec in self.records:
            if rec[3] is None and rec[4] in failed:
                rec[4] = int(self.rng_gw.choice(alive))
                if rec[6] is not None and rec[4] in rec[6]:
                    rec[3] = env.now
                    if cfg.warmup <= rec[0] < end:
                        self.n_done_measured += 1

    # ---------------- run ----------------
    def run(self):
        cfg, env = self.cfg, self.env
        env.process(self.generator())
        env.process(self.block_cutter())
        if cfg.failures:
            env.process(self.failure_process())
        end = cfg.warmup + cfg.measure
        env.run(until=end)
        limit = end + cfg.drain_limit
        while self.n_done_measured < self.n_measured and env.now < limit:
            env.run(until=min(env.now + 5.0, limit))
        return self

    def results(self):
        cfg = self.cfg
        end = cfg.warmup + cfg.measure
        m = [r for r in self.records if cfg.warmup <= r[0] < end]
        ok = [r for r in m if r[3] is not None]
        T = np.array([r[3] - r[0] for r in ok])
        n_unendorsable = sum(1 for r in m if r[5] == "unendorsable")
        Te = np.array([r[1] - r[0] for r in ok])
        To = np.array([r[2] - r[1] for r in ok])
        Tc = np.array([r[3] - r[2] for r in ok])
        # growth check: a stable system has similar means in the first and last fifths of the
        # measured window; a ratio well above 1 means the backlog is growing (unsustainable load)
        growth = np.nan
        if len(T) > 50:
            ta = np.array([r[0] for r in ok]); lo, hi = cfg.warmup, cfg.warmup + cfg.measure
            w = (hi - lo) / 5; a = T[(ta >= lo) & (ta < lo + w)]; b = T[(ta >= hi - w) & (ta < hi)]
            if len(a) and len(b):
                growth = b.mean() / a.mean()
        return dict(n=len(m), n_confirmed=len(ok), n_unendorsable=n_unendorsable, growth=growth,
                    stable=len(ok) == len(m) and len(m) > 0 and not (growth > 1.5),
                    mean=T.mean() if len(T) else np.nan,
                    p50=np.percentile(T, 50) if len(T) else np.nan,
                    p95=np.percentile(T, 95) if len(T) else np.nan,
                    p99=np.percentile(T, 99) if len(T) else np.nan,
                    endorse=Te.mean() if len(T) else np.nan,
                    order=To.mean() if len(T) else np.nan,
                    commit=Tc.mean() if len(T) else np.nan,
                    mean_block=np.mean(self.block_sizes) if self.block_sizes else np.nan,
                    times=(np.array([r[0] for r in ok]), T))


def run_pipeline(cfg: PipelineConfig) -> dict:
    return FabricPipeline(cfg).run().results()


# --------------------------------------------------------------------------------------------
# Reference designs (same measurement rules)
# --------------------------------------------------------------------------------------------
@dataclass
class QueueConfig:
    lam: float = 200.0
    mu: float = 250.0             # per-server rate; COMMON value across reference designs (D-1)
    c: int = 1                    # servers (1 = centralised M/M/1, >1 = parallel M/M/c)
    class_probs: Optional[list] = None   # priority classes (highest first) for non-preemptive priority
    warmup: float = 300.0
    measure: float = 600.0
    drain_limit: float = 600.0
    seed: int = 0


def run_queue(cfg: QueueConfig) -> dict:
    """M/M/c FCFS, or M/M/1 non-preemptive priority if class_probs is given."""
    env = simpy.Environment()
    ss = np.random.SeedSequence(cfg.seed); a, s, k = ss.spawn(3)
    ra, rs, rk = (np.random.default_rng(x) for x in (a, s, k))
    prio = cfg.class_probs is not None
    res = simpy.PriorityResource(env, capacity=cfg.c) if prio else simpy.Resource(env, capacity=cfg.c)
    recs = []; end = cfg.warmup + cfg.measure

    def customer(rec):
        req = res.request(priority=rec[2]) if prio else res.request()
        with req:
            yield req
            rec[3] = env.now
            yield env.timeout(rs.exponential(1.0 / cfg.mu))
        rec[1] = env.now

    def gen():
        while True:
            yield env.timeout(ra.exponential(1.0 / cfg.lam))
            if env.now >= end:
                return
            k_ = int(rk.choice(len(cfg.class_probs), p=cfg.class_probs)) if prio else 0
            rec = [env.now, None, k_, None]; recs.append(rec); env.process(customer(rec))

    env.process(gen()); env.run(until=end + cfg.drain_limit)
    m = [r for r in recs if cfg.warmup <= r[0] < end]
    ok = [r for r in m if r[1] is not None]
    T = np.array([r[1] - r[0] for r in ok]); Wq = np.array([r[3] - r[0] for r in ok])
    out = dict(n=len(m), n_confirmed=len(ok), stable=len(ok) == len(m) and len(m) > 0,
               mean=T.mean() if len(T) else np.nan, wq=Wq.mean() if len(T) else np.nan,
               p95=np.percentile(T, 95) if len(T) else np.nan,
               p99=np.percentile(T, 99) if len(T) else np.nan)
    if prio:
        K = np.array([r[2] for r in ok])
        out["class_sojourn"] = [T[K == k].mean() for k in range(len(cfg.class_probs))]
        out["class_wait"] = [Wq[K == k].mean() for k in range(len(cfg.class_probs))]
    return out


# --------------------------------------------------------------------------------------------
# Replications and statistics
# --------------------------------------------------------------------------------------------
def _run_one(args):
    run_fn, cfg = args
    r = run_fn(cfg)
    r.pop("times", None)            # large arrays are not needed across processes
    return r


def replicate(run_fn, cfg, n_reps=30, keys=("mean", "p95", "p99"), base_seed=0, n_jobs=1):
    """Independent replications (seed = base_seed + i). Returns per-key mean, 95% CI half-width,
    and the per-replication values. Statistics use the n_reps replication means as observations.
    n_jobs > 1 runs replications in parallel processes (e.g. n_jobs=6 on an 8-thread laptop);
    results are identical to n_jobs=1 because each replication has its own seed."""
    cfgs = [replace(cfg, seed=base_seed + i) for i in range(n_reps)]
    if n_jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=n_jobs) as ex:
            runs = list(ex.map(_run_one, [(run_fn, c_) for c_ in cfgs]))
    else:
        runs = [_run_one((run_fn, c_)) for c_ in cfgs]
    vals = {k: [] for k in keys}; stable = []
    for r in runs:
        stable.append(r["stable"])
        for k in keys:
            vals[k].append(r[k])
    out = {"stable_all": all(stable), "n_reps": n_reps}
    for k in keys:
        v = np.array(vals[k], dtype=float)
        half = stats.t.ppf(0.975, n_reps - 1) * v.std(ddof=1) / math.sqrt(n_reps) if n_reps > 1 else np.nan
        out[k] = (v.mean(), half, v)
    return out


def compare(vals_a, vals_b):
    """Paired comparison of two designs on common random numbers (same replication seeds):
    mean difference with 95% CI, and standardised effect size (paired Cohen's d)."""
    d = np.asarray(vals_a) - np.asarray(vals_b); n = len(d)
    half = stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / math.sqrt(n)
    return dict(diff=d.mean(), ci=(d.mean() - half, d.mean() + half), cohen_d=d.mean() / d.std(ddof=1))


# --------------------------------------------------------------------------------------------
# Warm-up justification (MSER-5, White 1997)
# --------------------------------------------------------------------------------------------
def mser5(arrival_times, values, t0=0.0, bin_width=None):
    """MSER-5 truncation point. Values (e.g. confirmation times) are averaged in batches of 5
    consecutive transactions; the truncation d minimises the standard error of the mean of the
    remaining batches, searched over the first half. Returns the truncation TIME (s)."""
    order = np.argsort(arrival_times); t = np.asarray(arrival_times)[order]; x = np.asarray(values)[order]
    nb = len(x) // 5
    if nb < 10:
        return np.nan
    xb = x[:nb * 5].reshape(nb, 5).mean(1); tb = t[:nb * 5].reshape(nb, 5)[:, 0]
    best, best_d = np.inf, 0
    for d in range(0, nb // 2):
        rest = xb[d:]; v = rest.var() / len(rest)
        if v < best:
            best, best_d = v, d
    return float(tb[best_d])


# --------------------------------------------------------------------------------------------
# Time-varying load profiles (picklable, so they work with n_jobs > 1)
# --------------------------------------------------------------------------------------------
class SurgeProfile:
    """Multiplier on lam: `mult` during [start, start + dur), 1 otherwise."""
    def __init__(self, start, dur, mult):
        self.start, self.dur, self.mult = start, dur, mult
    def __call__(self, t):
        return self.mult if self.start <= t < self.start + self.dur else 1.0


class RampProfile:
    """Multiplier rising linearly from m0 at `start` to m1 at `start + dur`, then held at m1."""
    def __init__(self, start, dur, m0, m1):
        self.start, self.dur, self.m0, self.m1 = start, dur, m0, m1
    def __call__(self, t):
        if t < self.start:
            return self.m0
        x = min((t - self.start) / self.dur, 1.0)
        return self.m0 + x * (self.m1 - self.m0)


def pairwise_table(values: dict, pairs: list, family_level=0.95):
    """Paired comparisons on common random numbers. values: design -> array of replication means
    (same seeds, same order). For each pair (a, b): mean difference a - b, its CI at the
    Bonferroni-adjusted level (family-wise coverage >= family_level), paired Cohen's d, paired t
    p-value and Holm-adjusted p-value. Observations are replication means (n = number of replications),
    never pooled transactions."""
    m = len(pairs); out = []
    for a, b in pairs:
        d = np.asarray(values[a]) - np.asarray(values[b]); n = len(d); sd = d.std(ddof=1)
        tcrit = stats.t.ppf(1 - (1 - family_level) / (2 * m), n - 1)
        half = tcrit * sd / math.sqrt(n)
        p = 2 * stats.t.sf(abs(d.mean()) / (sd / math.sqrt(n)), n - 1) if sd > 0 else 0.0
        out.append(dict(pair=(a, b), diff=d.mean(), ci=(d.mean() - half, d.mean() + half),
                        cohen_d=d.mean() / sd if sd > 0 else np.inf, p=p))
    order = np.argsort([r["p"] for r in out]); running = 0.0
    for rank, i in enumerate(order):                  # Holm step-down
        adj = min(1.0, (m - rank) * out[i]["p"]); running = max(running, adj); out[i]["p_holm"] = running
    return out
