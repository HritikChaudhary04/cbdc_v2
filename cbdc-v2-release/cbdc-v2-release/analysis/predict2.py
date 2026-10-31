import csv,glob,json,statistics as st,math
from params import blocks
from cbdc_v2_formulas import endorsement_time,formation_exact,road_kingman,commit_qna
base=dict(s0=0.01488,s1=0.0000494,v0=0.00868,v1=0.0005447)
cfg={'A':(50,2.0,3),'B10':(10,2.0,3),'B100':(100,2.0,3),'B500':(500,2.0,3),'T025':(50,0.25,3),'T1':(50,1.0,3),'Q1':(100,2.0,1),'Q2':(100,2.0,2),'Q4':(100,2.0,4),'Q5':(100,2.0,5)}
S={(r['block'],r['round']):r for r in csv.DictReader(open('campaign_stats.csv'))}
R=list(csv.DictReader(open('campaign_rounds.csv')))
print('block load | low-load-param model | per-load-param model | measured (healthy reps only*) | err low / per-load')
for (b,lab),r in sorted(S.items(),key=lambda k:(k[0][0],int(k[0][1].split('-')[1][:-3]))):
    if b not in cfg or not lab.startswith('uniform'): continue
    B,tau,q=cfg[b]; lam=float(lab.split('-')[1][:-3])
    reps=[x for x in R if x['block']==b and x['round']==lab]
    healthy=[x for x in reps if float(x['fail_frac'])<0.06 and float(x['steady_tps'])>0.97*lam]  # no congestion
    if not healthy: print(f'{b:5} {lam:4.0f} | no healthy rep'); continue
    e=st.mean(float(x['endorse_ms']) for x in healthy)/1000
    pts=[]
    for x in healthy:
        rd=glob.glob(f"*-{b}-rep{x['rep']}/[0-9][0-9]-{lab}")[0]; pts+=blocks(rd)
    N=st.mean(p[0] for p in pts); o=st.mean(p[1] for p in pts)/1000; c=st.mean(p[2] for p in pts)/1000
    ko=o/(base['s0']+base['s1']*N); kc=c/(base['v0']+base['v1']*N)
    def model(mu,s0,s1,v0,v1):
        return 1000*(endorsement_time('default',lam,mu,5,q)+formation_exact(lam,B,tau)+road_kingman(lam,B,tau,s0,s1)[0]+commit_qna(lam,B,tau,s0,s1,v0,v1)[0])
    m0=model(1/0.00246+50*3/5,base['s0'],base['s1'],base['v0'],base['v1'])
    m1=model(1/e+lam*q/5,base['s0']*ko,base['s1']*ko,base['v0']*kc,base['v1']*kc)
    meas=1000*st.mean(float(x['avg_lat_s']) for x in healthy)
    print(f"{b:5} {lam:4.0f} | {m0:7.0f} | {m1:7.0f} (e {e*1000:.1f} ms, order x{ko:.2f}, commit x{kc:.2f}) | {meas:6.0f} ({len(healthy)}/{len(reps)}) | {100*(m0-meas)/meas:+.0f}% / {100*(m1-meas)/meas:+.0f}%")
