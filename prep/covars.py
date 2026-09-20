import json, math, heapq, sys, numpy as np
"""Skog-, satellitt-, OSM- og gangtidsvariabler. Bruk: python prep/covars.py <områdemappe>"""
A=sys.argv[1]; D=f"{A}/data"; AREA=json.load(open(f"{A}/area.json"))
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
g=json.load(open(f'{D}/grid.json'))
N=576; M=1152
MX0,MY0,MX1,MY1=g['MX0'],g['MY0'],g['MX1'],g['MY1']
R=6378137.0
T=np.load(f'{D}/terrain.npz'); elev=T['elev']; slope=T['slope']
cell=(MX1-MX0)/N*math.cos(math.radians((g['SW'][0]+g['NE'][0])/2))
def ll2px(lat,lon,n):
    mx=math.radians(lon)*R; my=R*math.log(math.tan(math.pi/4+math.radians(lat)/2))
    return (mx-MX0)/(MX1-MX0)*n,(MY1-my)/(MY1-MY0)*n
def down2(a): return a.reshape(N,2,N,2).mean(axis=(1,3))
# ---------- SR16
def rgb(fn): return np.array(Image.open(fn).convert("RGBA")).astype(int)
def classify(im,table):
    out=np.full(im.shape[:2],np.nan)
    for (r,gg,b),v in table.items():
        m=(im[...,0]==r)&(im[...,1]==gg)&(im[...,2]==b)&(im[...,3]>0); out[m]=v
    return out
ramp=[(247,252,245),(229,245,224),(199,233,192),(161,217,155),(116,196,118),(65,171,93),(35,139,69),(0,109,44),(0,68,27),(0,40,15)]
tre=classify(rgb(f'{D}/sr16_SRRTRESLAG.png'),{(82,176,56):1,(205,170,101):2,(255,220,130):3})
bon=classify(rgb(f'{D}/sr16_SRRBONITET.png'),dict(zip(ramp[:8],[6,8,11,14,17,20,23,26])))
hgt=classify(rgb(f'{D}/sr16_SRRHOYDEM.png'),dict(zip(ramp,[1,3,5,7,9,11,13,15,16.5,19])))   # m
kro=classify(rgb(f'{D}/sr16_SRRKRONEDEK.png'),dict(zip(ramp,[5,15,25,35,45,55,65,75,85,95])))
vol=classify(rgb(f'{D}/sr16_SRRVOLMB.png'),{(204,236,230):50,(153,216,201):150,(102,194,164):250,(44,162,95):350,(0,109,44):450})
forest_hi=~np.isnan(tre)
def frac(cls,rad=1):
    a=(tre==cls).astype(float); w=forest_hi.astype(float)
    num=ndi.uniform_filter(a,2*rad+1); den=ndi.uniform_filter(w,2*rad+1)
    return down2(np.where(den>0,num/np.maximum(den,1e-9),0))
f_gran,f_furu,f_lauv=frac(1,2),frac(2,2),frac(3,2)       # ~50 m neighbourhood
def nanmean_down(a):
    v=np.nan_to_num(a); w=(~np.isnan(a)).astype(float)
    num=ndi.uniform_filter(v*1.0,5)*1; den=ndi.uniform_filter(w,5)
    return down2(np.where(den>0.05,num/np.maximum(den,1e-9),np.nan))
bon_d,hgt_d,kro_d,vol_d=[nanmean_down(x) for x in (bon,hgt,kro,vol)]
forest=down2(forest_hi.astype(float))>=0.5
print("forest share",forest.mean(),"gran/furu/lauv share of forest",[(tre==c).sum()/forest_hi.sum() for c in (1,2,3)])
# ---------- Sentinel-2
def idx(name):
    d=np.load(f'{D}/s2_{name}.npz'); f=lambda b: np.maximum(d[b],1.0)
    nd=(f('nir')-f('red'))/(f('nir')+f('red')); nm=(f('nir')-f('swir16'))/(f('nir')+f('swir16'))
    return down2(nd),down2(nm),d
ndvi_sp,ndmi_sp,dsp=idx('spring'); ndvi_la,ndmi_la,dla=idx('late')
decid=ndvi_la-ndvi_sp
water_s2=down2((dla['scl']==6).astype(float))>0.5
print("ndvi late forest mean",np.nanmean(ndvi_la[forest]),"spring",np.nanmean(ndvi_sp[forest]),"ndmi late",np.nanmean(ndmi_la[forest]))
# true-colour image for display
rgbim=np.dstack([dla['red'],dla['green'],dla['blue']]); v=np.clip(rgbim/1300.0,0,1)**0.55
Image.fromarray((v*255).astype(np.uint8)).save(f'{D}/s2_truecolor.png'); Image.fromarray((v*255).astype(np.uint8)).save(f'{D}/base_sat.jpg',quality=85)
# ---------- OSM rasters
hw=json.load(open(f'{D}/osm_highways.json'))['elements']; lu=json.load(open(f'{D}/osm_landuse.json'))['elements']
def draw_lines(ways,n,width=1):
    im=Image.new("L",(n,n),0); dr=ImageDraw.Draw(im)
    for w in ways:
        pts=[ll2px(p['lat'],p['lon'],n) for p in w['geometry']]
        if len(pts)>1: dr.line(pts,fill=255,width=width)
    return np.array(im)>0
def walkable(w):
    t=w.get('tags',{}); h=t.get('highway')
    if t.get('foot')=='no' or t.get('access') in ('private','no'): return False
    return h in ('path','footway','track','cycleway','steps','pedestrian','residential','service','unclassified','tertiary','living_street','secondary','bridleway')
walk=[w for w in hw if walkable(w)]
trail=[w for w in walk if w['tags']['highway'] in ('path','footway','track','cycleway','bridleway','steps')]
path_r=draw_lines(trail,M); d_path=down2(ndi.distance_transform_edt(~path_r))*cell/2
def polys(filt):
    im=Image.new("L",(M,M),0); dr=ImageDraw.Draw(im)
    for e in lu:
        t=e.get('tags',{})
        if not filt(t): continue
        if e['type']=='way' and 'geometry' in e:
            pts=[ll2px(p['lat'],p['lon'],M) for p in e['geometry']]
            if len(pts)>2: dr.polygon(pts,fill=255)
        elif e['type']=='relation':
            for mem in e.get('members',[]):
                if mem.get('role')=='outer' and 'geometry' in mem:
                    pts=[ll2px(p['lat'],p['lon'],M) for p in mem['geometry']]
                    if len(pts)>2: dr.polygon(pts,fill=255)
    return np.array(im)>0
water_osm=polys(lambda t:t.get('natural')=='water'); wet_osm=polys(lambda t:t.get('natural')=='wetland')
resid=polys(lambda t:t.get('landuse') in ('residential','industrial','commercial','retail'))
water=(down2(water_osm.astype(float))>0.4)|water_s2
wetl=down2(wet_osm.astype(float))>0.4
d_water=ndi.distance_transform_edt(~(water|wetl))*cell
d_edge=ndi.distance_transform_edt(forest)*cell          # distance into forest from nearest non-forest
d_resid=ndi.distance_transform_edt(~(down2(resid.astype(float))>0.4))*cell
forest&=~water
print("wetland cells",wetl.sum(),"water",water.sum())
# ---------- walking time: Dijkstra on path graph (Tobler) then raster spread off-trail
def elev_at(px,py):
    i=min(max(int(py),0),N-1); j=min(max(int(px),0),N-1); return elev[i,j]
adj={}
def key(p): return (round(p['lat'],7),round(p['lon'],7))
def tobler(dh,dx): return 6.0*math.exp(-3.5*abs(dh/max(dx,1e-6)+0.05))   # km/h
for w in walk:
    ge=w['geometry']; fac=0.85 if w['tags']['highway']=='path' else 1.0
    for a,b in zip(ge[:-1],ge[1:]):
        ka,kb=key(a),key(b)
        dx=math.hypot((a['lon']-b['lon'])*math.cos(math.radians(a['lat']))*111320,(a['lat']-b['lat'])*110950)
        if dx<=0: continue
        ea=elev_at(*ll2px(a['lat'],a['lon'],N)); eb=elev_at(*ll2px(b['lat'],b['lon'],N))
        adj.setdefault(ka,[]).append((kb,dx/1000/(tobler(eb-ea,dx)*fac)*60))
        adj.setdefault(kb,[]).append((ka,dx/1000/(tobler(ea-eb,dx)*fac)*60))
arv=json.load(open(f"{A}/{AREA['road_file']}"))['elements']
src=set(key(p) for e in arv for p in e['geometry'])
tt={k:0.0 for k in src if k in adj}; pq=[(0.0,k) for k in tt]; heapq.heapify(pq)
while pq:
    d,u=heapq.heappop(pq)
    if d>tt.get(u,1e9): continue
    for v,c in adj.get(u,[]):
        nd=d+c
        if nd<tt.get(v,1e9): tt[v]=nd; heapq.heappush(pq,(nd,v))
print("graph nodes",len(adj),"reached",len(tt))
time=np.full((N,N),np.inf)
for w in walk:                                   # densify edges onto raster
    ge=w['geometry']
    for a,b in zip(ge[:-1],ge[1:]):
        ta,tb=tt.get(key(a)),tt.get(key(b))
        if ta is None or tb is None: continue
        ax,ay=ll2px(a['lat'],a['lon'],N); bx,by=ll2px(b['lat'],b['lon'],N)
        n=int(max(abs(ax-bx),abs(ay-by))*2)+1
        for s in np.linspace(0,1,n+1):
            i,j=int(ay+(by-ay)*s),int(ax+(bx-ax)*s)
            if 0<=i<N and 0<=j<N: time[i,j]=min(time[i,j],ta+(tb-ta)*s)
tl=time.tolist(); el=elev.tolist(); wl=water.tolist()
pq=[(tl[i][j],i,j) for i in range(N) for j in range(N) if tl[i][j]<1e8]; heapq.heapify(pq)
nb=[(-1,-1,1.4142),(-1,0,1),(-1,1,1.4142),(0,-1,1),(0,1,1),(1,-1,1.4142),(1,0,1),(1,1,1.4142)]
while pq:
    d,i,j=heapq.heappop(pq)
    if d>tl[i][j]: continue
    for di,dj,dd in nb:
        a,b=i+di,j+dj
        if 0<=a<N and 0<=b<N and not wl[a][b]:
            dx=dd*cell; v=0.55*6.0*math.exp(-3.5*abs((el[a][b]-el[i][j])/dx+0.05))
            nd=d+dx/1000/v*60
            if nd<tl[a][b]: tl[a][b]=nd; heapq.heappush(pq,(nd,a,b))
wtime=np.array(tl); wtime[~np.isfinite(wtime)]=np.nan
print("walk time pct (forest)",np.nanpercentile(wtime[forest],[5,25,50,75,95]))
np.savez_compressed(f'{D}/covars.npz',f_gran=f_gran,f_furu=f_furu,f_lauv=f_lauv,bon=bon_d,hgt=hgt_d,kro=kro_d,vol=vol_d,forest=forest,
    ndvi_sp=ndvi_sp,ndvi_la=ndvi_la,ndmi_la=ndmi_la,ndmi_sp=ndmi_sp,decid=decid,water=water,wetl=wetl,d_path=d_path,d_water=d_water,d_edge=d_edge,d_resid=d_resid,wtime=wtime)
