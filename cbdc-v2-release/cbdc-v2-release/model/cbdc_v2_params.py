"""
cbdc_v2_params.py : the ONE place where parameters are set. Every notebook imports from here,
so all designs use a common load and a common capacity (reviewer issue D-1).

Service parameters MEASURED on the Fabric testbed at 25-50 TPS (2026-10-22, build log Entry 12; paper Sec. 5.3,
Table tab:stageparams). mu_e from the endorsement sojourn (2.46 ms) + lam*q/c at 50 TPS. Previous illustrative
values: mu_e=200, s0=0.020, s1=0.001, v0=0.010, v1=0.002, B_CHOSEN=9.
"""
from cbdc_v2_formulas import capacities

LAM_DESIGN = 200.0                 # design load, TPS (Nepal, paper Sec. 5)
NEPAL_MEAN = 41.0                  # FY2023/24 annual mean, TPS
RHO_MAX = 0.70                     # headroom rule (issue A-3)

# Fabric pipeline (paper Sec. 4.2-4.6)
PIPE = dict(mu_e=436.0, c=5, q=3, s0=0.01488, s1=0.0000494, v0=0.00868, v1=0.0005447, tau=2.0)
B_CHOSEN = 100                     # testbed-confirmed at LAM_DESIGN (decision 2026-10-22); the model-only rule picks B=5,
                                   # which the testbed rejects (B=10 congests at 150 TPS, B=50 metastable at 200 TPS)

# Equal-capacity rule (decision D-1 (a)): every reference design gets the pipeline's system
# capacity at the chosen configuration, so designs differ only in how work is organised.
CAPACITY = capacities(B_CHOSEN, **PIPE)["system"]       # ~310 TPS with illustrative values

# Reference designs at equal total capacity
MU_CENTRAL = CAPACITY              # M/M/1: one server
C_PARALLEL = 5
MU_PARALLEL = CAPACITY / C_PARALLEL  # M/M/5: five servers sharing the same total capacity
PRIORITY_CLASSES = ["government", "business", "retail"]
PRIORITY_SPLIT = [0.05, 0.20, 0.75]  # ASSUMED class shares (state as assumption; source at final check)
MU_PRIORITY = CAPACITY

# Simulation settings
N_REPS = 30
WARMUP = 300.0
MEASURE = 600.0

# Parallel replications on the laptop (8 threads): set to e.g. 6. Results do not depend on it.
N_JOBS = 1
