import csv,glob,re,json,statistics as st,numpy as np
def blocks(rd,skip=60):
    bo={int(x['block']):x for x in csv.DictReader(open(rd+'/blocks_orderer.csv',newline=''))}
    bp=[x for x in csv.DictReader(open(rd+'/blocks_peer.csv',newline='')) if 'inst1' in x['peer']]
    t0=min(float(x['committed_utc']) for x in bp)
    out=[]
    for x in bp:
        if float(x['committed_utc'])<t0+skip: continue
        b=int(x['block']); o=bo.get(b)
        if not o: continue
        ordr=float(o['written_leader_utc'])-float(o['created_utc'])
        out.append((int(x['n_tx']),ordr*1000,float(x['validate_ms'])+float(x['commit_ms'])))
    return out
pts=[]
for blk,lab in [('A','uniform-50tps'),('A','uniform-25tps'),('B10','uniform-50tps'),('B10','uniform-25tps'),('B100','uniform-50tps'),('B500','uniform-50tps'),('T025','uniform-50tps')]:
    for rd in glob.glob(f'*-{blk}-rep*/[0-9][0-9]-{lab}'):
        pts+= [(blk,)+p for p in blocks(rd)]
N=np.array([p[1] for p in pts]); O=np.array([p[2] for p in pts]); C=np.array([p[3] for p in pts])
for name,Y in [('order (Raft cut->written leader)',O),('commit (validate+commit at inst1)',C)]:
    A=np.vstack([np.ones_like(N),N]).T; coef,*_=np.linalg.lstsq(A,Y,rcond=None)
    print(name, 'a0=%.2f ms  a1=%.4f ms/tx'%tuple(coef), ' n=%d'%len(N))
    for blk in ['B10','T025','A','B100','B500']:
        m=[p for p in pts if p[0]==blk]; print('   %-5s N=%.0f  mean=%.2f ms'%(blk,st.mean(p[1] for p in m),st.mean((p[2] if 'order' in name else p[3]) for p in m)))
# endorsement per peer and gateway at 50 TPS
for blk in ['A','B100','B10']:
    e=[];g=[];s=[]
    for f in glob.glob(f'*-{blk}-rep*/[0-9][0-9]-uniform-50tps/summary.json'):
        d=json.load(open(f)); e.append(d['endorse_ms_peer_mean'])
        P=d['peers']; g.append(st.mean(P[p]['gateway']['Endorse_OK']['mean_s'] for p in P if P[p]['gateway']['Endorse_OK']['count'])*1000)
        s.append(st.mean(P[p]['gateway']['Submit_OK']['mean_s'] for p in P if P[p]['gateway']['Submit_OK']['count'])*1000)
    print(blk,'endorse/peer %.2f ms, gateway Endorse %.2f ms, Submit %.2f ms'%(st.mean(e),st.mean(g),st.mean(s)))
