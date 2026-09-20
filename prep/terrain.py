import json, math, heapq, sys, numpy as np, rasterio
"""Terrengvariabler fra 5 m-terrengmodell. Bruk: python prep/terrain.py <områdemappe>"""
A=sys.argv[1]; D=f"{A}/data"
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from pyproj import Transformer
g=json.load(open(f'{D}/grid.json'))
N=576; MX0,MY0,MX1,MY1=g['MX0'],g['MY0'],g['MX1'],g['MY1']
cm=(MX1-MX0)/N                       # mercator m per cell
latc=math.radians((g['SW'][0]+g['NE'][0])/2); k=math.cos(latc)
cell=cm*k                            # ground m per cell
print("cell ground m",cell)
# cell centres
xs=MX0+(np.arange(N)+0.5)*cm; ys=MY1-(np.arange(N)+0.5)*cm
XX,YY=np.meshgrid(xs,ys)
t=Transformer.from_crs(3857,25833,always_xy=True)
UX,UY=t.transform(XX,YY)
# --- DEM
with rasterio.open(f'{D}/dtm_utm33_5m.tif') as ds:
    dem5=ds.read(1).astype(np.float64); b=ds.bounds; res=ds.res[0]
col=(UX-b.left)/res-0.5; row=(b.top-UY)/res-0.5
dem5s=ndi.gaussian_filter(dem5,1.0)
elev=ndi.map_coordinates(dem5s,[row,col],order=1,mode='nearest')
elev_s=ndi.gaussian_filter(elev,1.0)
gy,gx=np.gradient(elev_s,cell)       # gy: d/d(row) -> southward positive
dzdx=gx; dzdy=-gy                    # y north
slope=np.arctan(np.hypot(dzdx,dzdy))
aspect=(np.degrees(np.arctan2(-dzdx,-dzdy))+360)%360   # downslope direction, 0=N, 90=E
# Heat load index, McCune & Keon 2002 eq.3
fold=np.radians(np.abs(180-np.abs(aspect-225)))
L=latc; S=np.minimum(slope,math.radians(60))
hli=np.exp(-1.467+1.582*np.cos(L)*np.cos(S)-1.5*np.cos(fold)*np.sin(S)*np.sin(L)-0.262*np.sin(L)*np.sin(S)+0.607*np.sin(fold)*np.sin(S))
# TPI 100 m and 300 m
def tpi(r):
    n=int(round(r/cell)); yy,xx=np.ogrid[-n:n+1,-n:n+1]; fp=(xx*xx+yy*yy<=n*n).astype(float); fp/=fp.sum()
    return elev-ndi.convolve(elev,fp,mode='nearest')
tpi100=tpi(100); tpi300=tpi(300)
# --- priority-flood fill + MFD flow accumulation -> TWI
def priority_flood(z,eps=1e-3):
    z=z.copy(); H,W=z.shape; closed=np.zeros((H,W),bool); pq=[]
    for i in range(H):
        for j in (0,W-1): heapq.heappush(pq,(z[i,j],i,j)); closed[i,j]=True
    for j in range(W):
        for i in (0,H-1):
            if not closed[i,j]: heapq.heappush(pq,(z[i,j],i,j)); closed[i,j]=True
    nb=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    while pq:
        e,i,j=heapq.heappop(pq)
        for di,dj in nb:
            a,b_=i+di,j+dj
            if 0<=a<H and 0<=b_<W and not closed[a,b_]:
                closed[a,b_]=True
                if z[a,b_]<=e: z[a,b_]=e+eps
                heapq.heappush(pq,(z[a,b_],a,b_))
    return z
zf=priority_flood(elev_s)
H=W=N
acc=np.ones((H,W))
order=np.argsort(-zf,axis=None)
nb=[(-1,-1,math.sqrt(2)),(-1,0,1),(-1,1,math.sqrt(2)),(0,-1,1),(0,1,1),(1,-1,math.sqrt(2)),(1,0,1),(1,1,math.sqrt(2))]
zl=zf.tolist(); accl=acc.tolist(); p=1.1
for idx in order.tolist():
    i,j=divmod(idx,W); z0=zl[i][j]; ws=[]; tot=0.0
    for di,dj,d in nb:
        a,b_=i+di,j+dj
        if 0<=a<H and 0<=b_<W:
            dz=z0-zl[a][b_]
            if dz>0:
                w=(dz/d)**p; ws.append((a,b_,w)); tot+=w
    if tot>0:
        f=accl[i][j]/tot
        for a,b_,w in ws: accl[a][b_]+=f*w
acc=np.array(accl)
sca=acc*cell
twi=np.log(sca/np.maximum(np.tan(slope),0.01))
print("twi",np.percentile(twi,[1,25,50,75,99]))
np.savez_compressed(f'{D}/terrain.npz',elev=elev,slope=slope,aspect=aspect,hli=hli,tpi100=tpi100,tpi300=tpi300,twi=twi,acc=acc,XX=XX,YY=YY,UX=UX,UY=UY)
print("elev",elev.min(),elev.max(),"slope deg p50/p95",np.degrees(np.percentile(slope,[50,95])),"hli",hli.min(),hli.max())
