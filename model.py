import json, math, glob, sys, datetime as dt, numpy as np
from scipy import ndimage as ndi
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.preprocessing import StandardScaler, SplineTransformer
from sklearn.metrics import roc_auc_score
from skimage.measure import find_contours
from skimage.feature import peak_local_max
from species_def import SPECIES
np.random.seed(1)
AREA_DIR=sys.argv[1] if len(sys.argv)>1 else 'areas/arvoll'; D=f'{AREA_DIR}/data'; AREA=json.load(open(f'{AREA_DIR}/area.json'))
SPECIES=[s for s in SPECIES if s[0]!="flatklokke"]
POISON={"giftslor","hvitflue"}
g=json.load(open(f'{D}/grid.json')); N=576; R=6378137.0; LATC=(g['SW'][0]+g['NE'][0])/2
MX0,MY0,MX1,MY1=g['MX0'],g['MY0'],g['MX1'],g['MY1']
C=dict(np.load(f'{D}/covars.npz')); T=dict(np.load(f'{D}/terrain.npz'))
forest=C['forest'].astype(bool); cell=(MX1-MX0)/N*math.cos(math.radians(LATC))
def ll2ij(lat,lon):
    mx=math.radians(lon)*R; my=R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
    return int((MY1-my)/(MY1-MY0)*N), int((mx-MX0)/(MX1-MX0)*N)
def ij2ll(i,j):
    mx=MX0+(j+0.5)*(MX1-MX0)/N; my=MY1-(i+0.5)*(MY1-MY0)/N
    return math.degrees(2*math.atan(math.exp(my/R))-math.pi/2), math.degrees(mx/R)
sig=lambda x:1/(1+np.exp(-x))
def fillna(a):
    a=a.copy(); a[~np.isfinite(a)]=np.nanmedian(a[forest]); return a
bon,hgt,kro,vol=[fillna(C[k]) for k in ('bon','hgt','kro','vol')]
slope_deg=np.degrees(T['slope'])
def z(a):
    v=a[forest]; return np.clip((a-np.mean(v))/np.std(v),-2.5,2.5)
# ================= 1. SDM: presence vs target-group background =================
recs=json.load(open(f'{D}/gbif_all.json'))
def good(r): 
    u=r.get('coordinateUncertaintyInMeters'); return u is not None and u<=100 and r.get('decimalLatitude')
tg=set(); pres={s[0]:[] for s in SPECIES}; obs_pts={s[0]:[] for s in SPECIES}; ncount={}
lat2sid={l:s[0] for s in SPECIES for l in s[2]}
flat_lat={l for sid_,_,lat_ in __import__('species_def').SPECIES if sid_=='flatklokke' for l in lat_}; n_flat=0
for r in recs:
    sid=lat2sid.get(r.get('species'))
    if sid: ncount[sid]=ncount.get(sid,0)+1
    if r.get('species') in flat_lat: n_flat+=1
    if not good(r): continue
    i,j=ll2ij(r['decimalLatitude'],r['decimalLongitude'])
    if not(0<=i<N and 0<=j<N): continue
    if sid: obs_pts[sid].append([round(r['decimalLatitude'],5),round(r['decimalLongitude'],5),r.get('year'),r.get('month')])
    if forest[i,j]:
        tg.add((i,j))
        if sid: pres[sid].append((i,j))
tg=sorted(tg); print("target-group background cells:",len(tg))
feat_names=['f_gran','f_furu','f_lauv','bon','hgt','vol','kro','ndvi_la','ndmi_la','decid','ndvi_sp','elev','slope','hli','twi','tpi100','tpi300','ld_path','ld_water','ld_edge']
F=[C['f_gran'],C['f_furu'],C['f_lauv'],bon,hgt,vol,kro,C['ndvi_la'],C['ndmi_la'],C['decid'],C['ndvi_sp'],T['elev'],slope_deg,T['hli'],T['twi'],T['tpi100'],T['tpi300'],np.log1p(C['d_path']),np.log1p(C['d_water']),np.log1p(C['d_edge'])]
X=np.stack([f[forest] for f in F],1); sc=StandardScaler().fit(X); Xs=np.clip(sc.transform(X),-3,3); Xall=np.hstack([Xs,Xs**2])
idx=-np.ones((N,N),int); idx[forest]=np.arange(forest.sum())
blk=lambda i,j:((i//105)+2*(j//105))%4
sdm={}
for sid,no,lat in SPECIES:
    pc=sorted(set(pres[sid])); 
    if len(pc)<15 or len(tg)<50:   # for få funn til en datamodell: bare ekspertmodell + eventuell funntetthet
        kd=np.zeros((N,N))
        for i,j in pres[sid]: kd[i,j]+=1
        kd=ndi.gaussian_filter(kd,6); kd=np.clip(kd/max(kd.max()*0.6,1e-9),0,1) if kd.max()>0 else kd
        sdm[sid]=dict(S=np.zeros((N,N)),auc=0.5,w=0.0,n_cells=len(pc),kde=kd); continue
    rows=[idx[i,j] for i,j in pc]+[idx[i,j] for i,j in tg]; y=np.r_[np.ones(len(pc)),np.zeros(len(tg))]
    fold=np.array([blk(i,j) for i,j in pc]+[blk(i,j) for i,j in tg]); Xa=Xall[rows]
    aucs=[]
    for k in range(4):
        tr,te=fold!=k,fold==k
        if y[te].sum()<4 or y[tr].sum()<8: continue
        m=LogisticRegression(C=0.05,class_weight='balanced',max_iter=2000).fit(Xa[tr],y[tr])
        aucs.append(roc_auc_score(y[te],m.decision_function(Xa[te])))
    auc=float(np.mean(aucs)) if aucs else 0.5
    m=LogisticRegression(C=0.05,class_weight='balanced',max_iter=2000).fit(Xa,y)
    eta=m.decision_function(Xall); lo,hi=np.percentile(eta,[5,99.5]); S=np.zeros((N,N)); S[forest]=np.clip((eta-lo)/(hi-lo),0,1)
    w=float(np.clip((auc-0.5)/0.25,0,1)*0.5) if len(pc)>=15 else 0.0
    kd=np.zeros((N,N)); 
    for i,j in pres[sid]: kd[i,j]+=1
    kd=ndi.gaussian_filter(kd,6); kd=np.clip(kd/max(kd.max()*0.6,1e-9),0,1)
    sdm[sid]=dict(S=S,auc=auc,w=w,n_cells=len(pc),kde=kd)
# ================= 2. Expert habitat =================
PAR={ # tree(g,f,l) h0  bon(mu,sd) moist(mu,sd) canopy slope tpi edge pick
 "kantarell":     ((.8,.6,1.0),12,(12,5),(.50,.20),0,1,0,.10,.30),
 "traktkantarell":((1.,.5,.2),15,(13,5),(.68,.20),+1,0,0,.0,.10),
 "steinsopp":     ((1.,.5,.6),12,(16,5),(.50,.22),0,0,0,.35,.15),
 "piggsopp":      ((1.,.4,.6),13,(15,5),(.58,.22),+1,0,0,.0,.10),
 "granmatriske":  ((1.,.05,.05),-14,(17,5),(.55,.22),0,0,0,.40,.05),
 "skrubb":        ((.25,.3,1.),0,(13,6),(.55,.25),0,0,0,.30,.05),
 "svartbrun":     ((.7,1.,.2),12,(11,4),(.45,.20),-1,0,1,.0,.05),
 "rimsopp":       ((.7,1.,.3),12,(10,4),(.45,.20),-1,0,1,.0,.05),
 "faresopp":      ((1.,.2,.1),15,(16,4),(.55,.20),+1,0,0,.0,.05),
 "trompet":       ((.3,.05,1.),0,(20,4),(.65,.20),0,0,0,.0,.05),
 "sandsopp":      ((.1,1.,.05),0,(8,3),(.35,.18),-1,0,1,.0,.0),
 "blodror":       ((1.,.5,.5),12,(13,5),(.50,.22),0,0,0,.0,.0),
 "giftslor":      ((1.,.3,.05),15,(12,4),(.72,.18),+1,0,0,.0,.0),
 "hvitflue":      ((1.,.5,.6),12,(12,5),(.60,.22),0,0,0,.0,.0)}
birch=np.clip((C['decid']-0.08)/0.25,0,1)
wet=0.45*z(T['twi'])-0.25*z(T['hli'])+0.30*z(C['ndmi_la'])-0.20*z(T['tpi100']); wet=wet/np.std(wet[forest])
def expert(sid):
    (wg,wf,wl),h0,(bm,bs),_,can,slp,tp,ae,ap=PAR[sid]
    tree=wg*C['f_gran']+wf*C['f_furu']+wl*C['f_lauv']+wl*0.5*birch*(1-C['f_lauv']); tree=np.clip(tree,0.02,1)
    if sid=="skrubb": tree=np.maximum(tree,0.9*birch)
    mat=1.0 if h0==0 else (sig((hgt-h0)/2.5) if h0>0 else 0.6+0.4*sig((-h0-hgt)/3))
    fb=np.maximum(np.exp(-0.5*((bon-bm)/bs)**2),0.15)**0.7
    fc=1.0 if can==0 else (0.5+0.5*sig((kro-60)/12) if can>0 else 0.6+0.4*sig((85-kro)/12))
    fs=0.65+0.35*sig((slope_deg-7)/3) if slp else 1.0
    ft=0.6+0.4*sig(T['tpi100']/4) if tp else 1.0
    fe=(1-ae)+ae*np.maximum(np.exp(-C['d_path']/25),np.exp(-C['d_edge']/40))
    fp=1-ap*np.exp(-C['d_path']/15)*np.exp(-np.nan_to_num(C['wtime'],nan=90)/60)
    H=tree*mat*fb*fc*fs*ft*fe*fp; H=np.where(forest,H,0); return np.clip(H/np.percentile(H[forest],99),0,1)
# ================= 3. Weather: bucket model + distributed-lag Poisson =================
wj=json.load(open(f'{D}/weather.json')); arch=json.load(open(f'{D}/weather_archive.json'))['daily']; fc=wj['daily']
TODAY=dt.date.fromisoformat(wj['fetched'])
A={d:(p,t,tn,e) for d,p,t,tn,e in zip(arch['time'],arch['precipitation_sum'],arch['temperature_2m_mean'],arch['temperature_2m_min'],arch['et0_fao_evapotranspiration']) if None not in (p,t,tn,e)}
Fc={d:(p,t,tn,e) for d,p,t,tn,e in zip(fc['time'],fc['precipitation_sum'],fc['temperature_2m_mean'],fc['temperature_2m_min'],fc['et0_fao_evapotranspiration']) if None not in (p,t,tn,e)}
print('forecast-API days:',min(Fc),max(Fc),len(Fc))
ov=[d for d in Fc if d in A and d<=(TODAY-dt.timedelta(7)).isoformat()]
pr=sum(A[d][0] for d in ov)/max(sum(Fc[d][0] for d in ov),1); toff=np.mean([A[d][1]-Fc[d][1] for d in ov]); pr_c=float(np.clip(pr,0.7,1.4))
print(f"overlap {len(ov)} d: ERA5/MET precip ratio {pr:.2f} (used {pr_c:.2f}), temp offset {toff:+.2f}")
d0=dt.date(2007,10,1); d1=dt.date.fromisoformat(max(Fc)); days=[d0+dt.timedelta(n) for n in range((d1-d0).days+1)]
P=np.zeros(len(days)); Tm=np.zeros(len(days)); Tn=np.zeros(len(days)); E=np.zeros(len(days))
for n,d in enumerate(days):
    s=d.isoformat()
    if s in Fc: p,t,tn,e=Fc[s]; P[n],Tm[n],Tn[n],E[n]=p*pr_c,t+toff,tn+toff,e
    elif s in A: P[n],Tm[n],Tn[n],E[n]=A[s]
    else: P[n],Tm[n],Tn[n],E[n]=P[n-1]*0,Tm[n-1],Tn[n-1],E[n-1]
WMAX=50.0; Wb=np.zeros(len(days)); w=25.0
for n in range(len(days)):
    w=min(WMAX,max(0.0,w+0.8*P[n]-0.9*E[n])) if Tm[n]>0 else w; Wb[n]=w
theta=Wb/WMAX
def rsum(a,lo,hi):   # sum over days t-hi..t-lo
    c=np.r_[0,np.cumsum(a)]; out=np.zeros(len(a))
    for t in range(len(a)):
        a0,a1=max(0,t-hi),max(0,t-lo+1); out[t]=c[a1]-c[a0]
    return out
R1,R2,R3,R4,R5=[np.sqrt(rsum(P,lo,hi)) for lo,hi in ((0,6),(7,13),(14,20),(21,27),(28,41))]
T14=rsum(Tm,0,13)/14-12.0; frost=rsum((Tn<0).astype(float),0,9)
Wx=np.stack([R1,R2,R3,R4,R5,theta,T14,T14**2,frost],1); wnames=['regn 0–6 d','regn 7–13 d','regn 14–20 d','regn 21–27 d','regn 28–41 d','vannbalanse','temp 14 d','temp²','frostdøgn']
doy=np.array([d.timetuple().tm_yday for d in days]); yr=np.array([d.year for d in days]); di={d:n for n,d in enumerate(days)}
train=(yr>=2008)&(yr<=2025)&(doy>=152)&(doy<=334)
wsc=StandardScaler().fit(Wx[train]); Wz=wsc.transform(Wx)
spl=SplineTransformer(n_knots=6,degree=3,include_bias=False).fit(np.arange(152,335)[:,None])
years=list(range(2008,2026))
def design(rows_t,rows_y,with_w=True):
    S_=spl.transform(np.clip(doy[rows_t],152,334)[:,None]); Y_=np.zeros((len(rows_t),len(years)))
    for k,y in enumerate(rows_y): Y_[k,years.index(y)]=1
    return np.hstack([Wz[rows_t],S_,Y_]) if with_w else np.hstack([S_,Y_])
wk_t=[];wk_y=[];wk_key=[]
for y in years:
    for k in range(26):
        e=dt.date(y,6,1)+dt.timedelta(7*k+6); wk_t.append(di[e]); wk_y.append(y); wk_key.append((y,k))
wk_t=np.array(wk_t)
def weekly_counts(sid):
    cnt={k:0 for k in wk_key}; n=0
    for fn in glob.glob(f'{D}/reg/{sid}_*.json'):
        for y,mo,da in json.load(open(fn)):
            if not(y and mo and da): continue
            try: d=dt.date(y,mo,da)
            except: continue
            k=(d-dt.date(y,6,1)).days//7
            if (y,k) in cnt: cnt[(y,k)]+=1; n+=1
    return np.array([cnt[k] for k in wk_key],float),n
Xw=design(wk_t,wk_y); X0=design(wk_t,wk_y,False)
def d2(y,mu): 
    dev=lambda y,m:2*np.sum(np.where(y>0,y*np.log(np.maximum(y,1e-12)/m),0)-(y-m)); return 1-dev(y,mu)/dev(y,np.full_like(y,y.mean()))
fits={}; ycounts={}
for sid,no,lat in SPECIES: ycounts[sid],_=weekly_counts(sid)
myc=[s[0] for s in SPECIES]; ypool=sum(ycounts[s]/max(ycounts[s].sum(),1) for s in myc)*200
mp=PoissonRegressor(alpha=0.02,max_iter=1000).fit(Xw,ypool); beta_pool=mp.coef_[:9]
print("pooled weather coefs:",dict(zip(wnames,np.round(beta_pool,3))))
allD=np.arange(len(days))
for sid,no,lat in SPECIES:
    y=ycounts[sid]; n=y.sum()
    m1=PoissonRegressor(alpha=0.02,max_iter=1000).fit(Xw,y); m0=PoissonRegressor(alpha=0.02,max_iter=1000).fit(X0,y)
    # leave-years-out CV gain from weather
    gain=[]
    for f in range(3):
        te=np.array([(yy-2008)%3==f for yy in wk_y]); 
        a=PoissonRegressor(alpha=0.02,max_iter=1000).fit(Xw[~te],y[~te]); b=PoissonRegressor(alpha=0.02,max_iter=1000).fit(X0[~te],y[~te])
        # year effect unknown for held-out years -> rescale predictions to the held-out total
        pa=a.predict(Xw[te]); pb=b.predict(X0[te]); pa*=y[te].sum()/pa.sum(); pb*=y[te].sum()/pb.sum()
        gain.append(d2(y[te],pa)-d2(y[te],pb))
    sh=n/(n+300.0); beta=sh*m1.coef_[:9]+(1-sh)*beta_pool; beta[8]=min(beta[8],0.0); beta[0]=max(beta[0],-0.15)
    sc_=m1.coef_[9:9+spl.n_features_out_]
    seas=np.exp(spl.transform(np.arange(152,335)[:,None])@sc_); seas/=seas.max()
    ew=np.exp(Wz@beta); clim=np.array([ew[(doy==dd)&(yr>=2008)&(yr<=2025)].mean() for dd in range(152,335)])
    clim=ndi.uniform_filter1d(clim,15,mode='nearest')
    fits[sid]=dict(n=int(n),beta=beta,seas=seas,clim=clim,ew=ew,d2w=float(d2(y,m1.predict(Xw))),d2s=float(d2(y,m0.predict(X0))),cvgain=float(np.nan_to_num(np.mean(gain))))
def phi_series(sid,d_from,d_to):
    f=fits[sid]; out=[]
    for n in range(di[d_from],di[d_to]+1):
        dd=int(np.clip(doy[n],152,334))-152; S_=f['seas'][dd]; A_=f['ew'][n]/f['clim'][dd]
        out.append((days[n].isoformat(),float(S_),float(A_),float(1-math.exp(-1.2*S_*A_))))
    return out
# ================= 4. Probability today =================
tn=di[TODAY]; th=float(theta[tn]); m_eff=sig(wet+2.5*(th-0.55))
nloc=sum(ncount.values()); lamn={s[0]:(ncount.get(s[0],0) if nloc>=500 else fits[s[0]]['n']) for s in SPECIES}; nmax=max(max(lamn.values()),1); OUT={}; grids={}
print('local records',nloc,'| lambda from',('local' if nloc>=500 else 'regional'),'counts')
print(f"\ntheta today {th:.2f}  | R7={R1[tn]**2:.0f} R8-14={R2[tn]**2:.0f} R15-21={R3[tn]**2:.0f} R22-28={R4[tn]**2:.0f} mm, T14={T14[tn]+12:.1f}")
print(f"{'art':15s} {'n':>4s} {'celler':>6s} {'AUC':>5s} {'w':>4s} {'nReg':>5s} {'D2s':>5s} {'D2w':>5s} {'cvΔ':>6s} {'S':>5s} {'A':>5s} {'Phi':>5s} {'Pmean':>6s} {'Pmax':>5s} {'ha>0.3':>7s}")
for sid,no,lat in SPECIES:
    He=expert(sid); s=sdm[sid]; w_=s['w']
    H=np.where(forest,(np.maximum(He,1e-3)**(1-w_))*(np.maximum(s['S'],1e-3)**w_),0); H=1-(1-H)*(1-0.5*s['kde']); H=np.where(forest,H,0)
    mu,sd=PAR[sid][3]; M=np.exp(-0.5*((m_eff-mu)/sd)**2)
    ser=phi_series(sid,TODAY-dt.timedelta(30),d1); today=[x for x in ser if x[0]==TODAY.isoformat()][0]
    lam=0.7+1.5*math.sqrt(lamn[sid]/nmax)
    Pm=np.where(forest,1-np.exp(-lam*H*M*today[3]),0); Pm=ndi.gaussian_filter(Pm,0.8)*forest
    grids[sid]=Pm
    print(f"{sid:15s} {ncount.get(sid,0):4d} {s['n_cells']:6d} {s['auc']:5.2f} {w_:4.2f} {fits[sid]['n']:5d} {fits[sid]['d2s']:5.2f} {fits[sid]['d2w']:5.2f} {fits[sid]['cvgain']:+6.3f} {today[1]:5.2f} {today[2]:5.2f} {today[3]:5.2f} {Pm[forest].mean():6.3f} {Pm.max():5.2f} {(Pm>0.3).sum()*cell*cell/1e4:7.1f}")
    OUT[sid]=dict(no=no,lat=lat,poison=sid in POISON,n=ncount.get(sid,0),auc=round(s['auc'],2),w=round(w_,2),nreg=fits[sid]['n'],cvgain=round(fits[sid]['cvgain'],3),
                  S=round(today[1],2),A=round(today[2],2),phi=round(today[3],2),series=[[d_,round(p_,3)] for d_,_,_,p_ in ser],lam=round(lam,2),
                  beta=dict(zip(wnames,[round(float(b),3) for b in fits[sid]['beta']])),obs=obs_pts[sid],pmax=round(float(Pm.max()),2))
edible=[s[0] for s in SPECIES if s[0] not in POISON]
Esum=np.sum([grids[s] for s in edible],axis=0); ESCALE=float(math.ceil(Esum.max())); grids['alle']=Esum/ESCALE; print('expected edible species: max',Esum.max(),'mean forest',Esum[forest].mean(),'scale',ESCALE)
# ================= 5. Hotspots, isochrones, export =================
waters=[]
for e in json.load(open(f'{D}/osm_landuse.json'))['elements']:
    t=e.get('tags',{})
    if t.get('natural')=='water' and t.get('name'):
        ge=e.get('geometry') or [p for m in e.get('members',[]) if 'geometry' in m for p in m['geometry']]
        if ge: waters.append((t['name'],np.mean([p['lat'] for p in ge]),np.mean([p['lon'] for p in ge])))
END=tuple(AREA['end'])
def dist_bear(lat,lon):
    dy=(lat-END[0])*110950; dx=(lon-END[1])*111320*math.cos(math.radians(lat)); d=math.hypot(dx,dy)
    b=(math.degrees(math.atan2(dx,dy))+360)%360; return d,["N","NØ","Ø","SØ","S","SV","V","NV"][int((b+22.5)//45)%8]
wt=np.nan_to_num(C['wtime'],nan=999)
for sid in list(OUT)+['alle']:
    Ps=ndi.gaussian_filter(grids[sid],2.5); Ps[wt>45]=0
    pk=peak_local_max(Ps,min_distance=26,num_peaks=6,exclude_border=5); hs=[]
    for i,j in pk:
        if Ps[i,j]<0.02: continue
        la,lo=ij2ll(i,j); d,b=dist_bear(la,lo); near=min(waters,key=lambda w_:math.hypot((w_[1]-la)*110950,(w_[2]-lo)*55700)) if waters else None
        nd=math.hypot((near[1]-la)*110950,(near[2]-lo)*55700) if near else 1e9
        hs.append(dict(lat=round(la,5),lon=round(lo,5),p=round(float(grids[sid][max(0,i-2):i+3,max(0,j-2):j+3].mean()),2),min=int(round(wt[i,j])),d=int(round(d/10)*10),b=b,near=near[0] if nd<450 else None,elev=int(T['elev'][i,j])))
    if sid=='alle': OUT['alle']=dict(no="Alle matsopper samlet",lat=[],poison=False,hot=hs,pmax=round(float(grids['alle'].max()),2),escale=ESCALE)
    else: OUT[sid]['hot']=hs
iso={}
wts=ndi.gaussian_filter(np.nan_to_num(C['wtime'],nan=200),2)
for lev in (15,30,45,60):
    ls=[]
    for c in find_contours(wts,lev):
        if len(c)<40: continue
        ls.append([[round(v,5) for v in ij2ll(p[0]-0.5,p[1]-0.5)] for p in c[::4]])
    iso[lev]=ls
arv=[[[round(p['lat'],5),round(p['lon'],5)] for p in e['geometry']] for e in json.load(open(f"{AREA_DIR}/{AREA['road_file']}"))['elements']]
wsum=dict(r7=round(float(R1[tn]**2/pr_c)),r14=round(float((R1[tn]**2+R2[tn]**2)/pr_c)),r30=round(float(sum(Fc[(TODAY-dt.timedelta(k)).isoformat()][0] for k in range(30)))),
          t10=round(float(np.mean([Fc[(TODAY-dt.timedelta(k)).isoformat()][1] for k in range(10)])),1),tmin10=round(float(min(Fc[(TODAY-dt.timedelta(k)).isoformat()][2] for k in range(10))),1),
          theta=round(th,2),fc=[[d,Fc[d][0],Fc[d][2]] for d in sorted(Fc) if d>TODAY.isoformat()])
from PIL import Image
import io,base64
def png8(a,k=100):
    b=io.BytesIO(); Image.fromarray(np.clip(np.round(a*k),0,255).astype(np.uint8),'L').save(b,'PNG',optimize=True); return base64.b64encode(b.getvalue()).decode()
pngs={k:png8(v) for k,v in grids.items()}; pngs['_walk']=png8(np.clip(np.nan_to_num(C['wtime'],nan=127),0,127),1); print("overlay png kB:",{k:len(v)//1024 for k,v in pngs.items()})
json.dump(dict(species=OUT,order=['alle']+[s[0] for s in SPECIES],iso=iso,arv=arv,weather=wsum,bounds=[list(g['SW']),list(g['NE'])],N=N,
               forest_share=float(forest.mean()),tg=len(tg),nrec=len(recs),n_flat=n_flat,pooled=dict(zip(wnames,[round(float(b),3) for b in beta_pool])),
               today=TODAY.isoformat(),d1=d1.isoformat(),area=AREA),open(f'{D}/model_out.json','w'))
json.dump(pngs,open(f'{D}/model_png.json','w')); np.savez_compressed(f'{D}/grids.npz',**grids)
for sid in ('alle','traktkantarell','kantarell','steinsopp'):
    print(sid,[(h['p'],h['min'],h['d'],h['b'],h['near']) for h in OUT[sid]['hot']])
