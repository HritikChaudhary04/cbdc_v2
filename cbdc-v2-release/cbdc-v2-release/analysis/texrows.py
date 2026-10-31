import pickle,csv,statistics as st,glob,math
from ext2 import pred,cfg,wq,e0,s0,s1,v0,v1,H,formation_exact,road_kingman,commit_qna
from params import blocks
rows=pickle.load(open('rows.pkl','rb')); S={(r['block'],r['round']):r for r in csv.DictReader(open('campaign_stats.csv'))}
R=list(csv.DictReader(open('campaign_rounds.csv')))
d0=25
name={'B10':'$B{=}10$, $q{=}3$','A':'$B{=}50$, $q{=}3$','B100':'$B{=}100$, $q{=}3$','B500':'$B{=}500$, $q{=}3$','Q1':'$B{=}100$, $q{=}1$','Q5':'$B{=}100$, $q{=}5$','T025':'$B{=}50$, $\\tau{=}0.25$\\,s'}
sel=[('B10',25),('B10',50),('B10',100),('A',25),('A',50),('A',100),('A',150),('B100',50),('B100',150),('B100',200),('B500',50),('Q1',200),('Q5',200),('T025',150)]
base=dict(s0=s0,s1=s1,v0=v0,v1=v1)
for b,l in sel:
    r=next(x for x in rows if x['b']==b and x['lam']==l); g=S[(b,f'uniform-{l}tps')]
    B,tau,q=cfg[b]
    m0=1000*(H(q)*e0+formation_exact(l,B,tau)+road_kingman(l,B,tau,s0,s1)[0]+commit_qna(l,B,tau,s0,s1,v0,v1)[0])
    # per-load params
    H_=[x for x in R if x['block']==b and x['round']==f'uniform-{l}tps' and float(x['fail_frac'])<0.06 and float(x['steady_tps'])>0.97*l]
    pts=[];
    for x in H_: pts+=blocks(glob.glob(f"*-{b}-rep{x['rep']}/[0-9][0-9]-uniform-{l}tps")[0])
    N=st.mean(p[0] for p in pts); ko=st.mean(p[1] for p in pts)/1000/(s0+s1*N); kc=st.mean(p[2] for p in pts)/1000/(v0+v1*N)
    e=st.mean(float(x['endorse_ms']) for x in H_)/1000
    m1=1000*(H(q)*e+formation_exact(l,B,tau)+road_kingman(l,B,tau,s0*ko,s1*ko)[0]+commit_qna(l,B,tau,s0*ko,s1*ko,v0*kc,v1*kc)[0])
    m2=pred(r,l*(wq[1]+wq[0]*q),d0)
    meas=1000*float(g['lat_mean']); ci=1000*float(g['lat_ci'])
    f=lambda v:f"{v:.0f} ({100*(v-meas)/meas:+.0f})"
    print(f"{name[b]} & {l} & ${meas:.0f} \\pm {ci:.0f}$ & {f(m0)} & {f(m1)} & {f(m2)} \\\\")
