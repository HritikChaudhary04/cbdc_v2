import json,glob,statistics as st,re
def cpu(f):
    d=json.load(open(f)); c=d['cpu_percent_mean']
    sut=sum(v for k,v in c.items() if ('peer0' in k or 'orderer' in k))  # peers, orderers, chaincode
    return sut/100
for b in ['B10','A','B100','B500','Q1','Q5','T025']:
    print(b, end=' ')
    for lab in ['uniform-25tps','uniform-50tps','uniform-100tps','uniform-150tps','uniform-200tps']:
        fs=glob.glob(f'*-{b}-rep*/[0-9][0-9]-{lab}/summary.json')
        if not fs: continue
        lam=int(re.search(r'(\d+)tps',lab).group(1)); v=[cpu(f) for f in fs]
        print(f"| {lam}: {st.mean(v):.2f} cores ({1000*st.mean(v)/lam:.1f} ms/tx)", end=' ')
    print()
d=json.load(open(glob.glob('*-A-rep1/[0-9][0-9]-uniform-50tps/summary.json')[0]))['cpu_percent_mean']; print(sorted(d.items()))
