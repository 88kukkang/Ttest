import re,sys,json
def parse(t):
    out=[]
    for p in re.findall(r"fn_osPop\(((?:'[^']*',?)+)\)",t):
        a=re.findall(r"'([^']*)'",p)
        if len(a)<32 or '+' in a[2]: continue
        out.append(dict(prem=a[1],gas=a[2],dsl=a[3],x=a[11],y=a[12],self=a[19],brand=a[23],name=a[22],addr=a[25],id=a[31]))
    return out
if __name__=='__main__':
    t=open(sys.argv[1],encoding='utf-8',errors='ignore').read(); r=parse(t); print(len(r)); print(r[:2])
