import csv,glob,os,statistics as st
from datetime import datetime,timezone
def ts(s): return datetime.strptime(s.replace('Z',''),'%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc).timestamp()
def rows(f): return list(csv.DictReader(open(f,newline='')))
print("=== E: committed TPS at inst1 in 10 s bins relative to the stop (t=0); restart ~48 s")
for d in sorted(glob.glob('*E-q*-failure')):
    r=glob.glob(d+'/02-*')[0]; ev=open(r+'/events.txt').read().splitlines()
    t0=ts(ev[0].split()[0]); stop=ts(ev[1].split()[0]); start=ts(ev[2].split()[0])
    bp=rows(r+'/blocks_peer.csv'); bo={int(x['block']):float(x['created_utc']) for x in rows(r+'/blocks_orderer.csv')}
    i1=[(float(x['committed_utc']),int(x['n_tx']),int(x['block'])) for x in bp if 'inst1' in x['peer']]
    bins={}
    for t,n,b in i1:
        k=int((t-stop)//10)*10; bins[k]=bins.get(k,0)+n
    line=' '.join(f"{k:+d}:{bins.get(k,0)/10:.0f}" for k in range(-40,100,10))
    # catch-up of inst4: last block committed by inst4 lagging >2 s behind orderer creation
    i4=sorted((int(x['block']),float(x['committed_utc'])) for x in bp if 'inst4' in x['peer'])
    lag_after=[(c-bo[b]) for b,c in i4 if c>start and b in bo]
    cu=None
    for b,c in i4:
        if c>start and b in bo and c-bo[b]<1.0: cu=c-start; break
    # commit lag at inst1 before/during/after
    lag=lambda a,b_: st.mean([t-bo[bb] for t,n,bb in i1 if a<=t<b_ and bb in bo]) if any(a<=t<b_ for t,n,bb in i1) else float('nan')
    print(d[16:].ljust(22),line,f"| inst1 lag s before/during/after {lag(stop-40,stop):.2f}/{lag(stop+2,start):.2f}/{lag(start+20,start+90):.2f} | inst4 caught up {cu:.1f} s after restart" if cu else "| no catch-up found")
print("\n=== F: committed TPS at inst1 (10 s bins from round start) and mean commit lag per phase")
for d in sorted(glob.glob('*F-rep*')):
    r=glob.glob(d+'/02-*')[0]
    bp=rows(r+'/blocks_peer.csv'); bo={int(x['block']):float(x['created_utc']) for x in rows(r+'/blocks_orderer.csv')}
    i1=sorted((float(x['committed_utc']),int(x['n_tx']),int(x['block'])) for x in bp if 'inst1' in x['peer'])
    T0=min(bo.values())
    bins={}
    for t,n,b in i1: k=int((t-T0)//10)*10; bins[k]=bins.get(k,0)+n
    print(d[16:].ljust(8),' '.join(f"{bins.get(k,0)/10:.0f}" for k in range(0,310,10)))
    for a,b_ in [(10,100),(100,110),(110,200),(200,210),(210,300)]:
        L=[t-bo[bb] for t,n,bb in i1 if T0+a<=t<T0+b_ and bb in bo]; S=[n for t,n,bb in i1 if T0+a<=t<T0+b_]
        print(f"   {a:3d}-{b_:3d}s: lag {st.mean(L)*1000:6.0f} ms, block size {st.mean(S):5.1f}" if L else f"   {a}-{b_}: none")
