import json,glob,os,re,csv,statistics as st,math
T=2.776  # t_{0.975,4}
def caliper(rd):
    h=open(rd+'/report.html').read(); s=h.split('id="benchmarksummary"')[1].split('</table>')[0]
    r=re.findall(r'<tr>\s*(.*?)\s*</tr>',s,re.S)[1]
    c=[re.sub('<.*?>','',x).strip() for x in re.findall(r'<td>(.*?)</td>',r)]
    return dict(succ=int(c[1]),fail=int(c[2]),avg=float(c[6]),mx=float(c[4]))
def win_stage(rd,skip=60):
    bo={int(x['block']):float(x['created_utc']) for x in csv.DictReader(open(rd+'/blocks_orderer.csv',newline=''))}
    bp=[x for x in csv.DictReader(open(rd+'/blocks_peer.csv',newline='')) if 'inst1' in x['peer']]
    if not bp: return None
    t0=min(float(x['committed_utc']) for x in bp); t1=max(float(x['committed_utc']) for x in bp)
    w=[x for x in bp if t0+skip<float(x['committed_utc'])<=t1-5 and int(x['block']) in bo]
    if not w: return None
    lag=[float(x['committed_utc'])-bo[int(x['block'])] for x in w]
    return dict(lag_ms=1000*st.mean(lag),val_ms=st.mean(float(x['validate_ms']) for x in w),bsize=st.mean(int(x['n_tx']) for x in w))
rows=[]
for d in sorted(glob.glob('2026*')):
    blk=re.sub(r'^[0-9-]+-','',d); m=re.match(r'(.+)-rep(\d)$',blk)
    if not m or blk.startswith(('E-','F-')): continue
    b,rep=m.group(1),int(m.group(2))
    for rd in sorted(glob.glob(d+'/[0-9][0-9]-*')):
        lab=rd.split('/')[-1][3:]
        if lab.startswith('warmup'): continue
        try: S=json.load(open(rd+'/summary.json')); C=caliper(rd)
        except Exception as e: print('skip',rd,e); continue
        W=win_stage(rd) or {}
        tot=C['succ']+C['fail']
        rows.append(dict(block=b,rep=rep,round=lab,avg_lat_s=C['avg'],max_lat_s=C['mx'],fail_frac=C['fail']/tot,
            steady_tps=S['steady_window']['tps'],valid=S['valid'],mvcc=S['mvcc_conflicts'],mism=S['endorse_mismatch_aborted'],
            endorse_ms=S['endorse_ms_peer_mean'],raft_ms=S['dist_ms']['raft_cut_to_written']['mean'],fsync_ms=S['raft_fsync_ms_leader']['mean'],
            win_commit_lag_ms=W.get('lag_ms'),win_validate_ms=W.get('val_ms'),block_size=W.get('bsize'),leader_changes=sum(S['leader_changes'].values())))
with open('campaign_rounds.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def agg(v):
    v=[x for x in v if x is not None]; n=len(v); m=st.mean(v); sd=st.stdev(v) if n>1 else 0
    return m,T*sd/math.sqrt(n) if n>1 else 0,min(v),max(v),n
groups={}
for r in rows: groups.setdefault((r['block'],r['round']),[]).append(r)
def load(lab): return int(re.search(r'(\d+)tps',lab).group(1))
out=[]
for (b,lab),g in sorted(groups.items(),key=lambda k:(k[0][0],k[0][1].split('-')[0],load(k[0][1]))):
    L=agg([x['avg_lat_s'] for x in g]); TP=agg([x['steady_tps'] for x in g]); F=agg([100*x['fail_frac'] for x in g])
    E=agg([x['endorse_ms'] for x in g]); CL=agg([x['win_commit_lag_ms'] for x in g])
    out.append(dict(block=b,round=lab,n=L[4],lat_mean=round(L[0],3),lat_ci=round(L[1],3),lat_min=L[2],lat_max=L[3],
        tps_mean=round(TP[0],1),tps_ci=round(TP[1],1),fail_pct=round(F[0],2),fail_ci=round(F[1],2),
        endorse_ms=round(E[0],1),endorse_ci=round(E[1],1),commit_lag_ms=round(CL[0],0),commit_lag_ci=round(CL[1],0)))
with open('campaign_stats.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(rows),'rounds;',len(out),'groups')
for o in out: print(f"{o['block']:5} {o['round']:15} n={o['n']} lat {o['lat_mean']:.3f}±{o['lat_ci']:.3f} [{o['lat_min']:.2f},{o['lat_max']:.2f}] tps {o['tps_mean']:.1f}±{o['tps_ci']:.1f} fail {o['fail_pct']:.1f}% endorse {o['endorse_ms']} lag {o['commit_lag_ms']:.0f}±{o['commit_lag_ci']:.0f}")
