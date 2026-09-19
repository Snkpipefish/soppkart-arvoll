import json, numpy as np, rasterio, sys
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from rasterio.crs import CRS
g=json.load(open('data/grid.json'))
N=1152
dst_tr=from_bounds(g['MX0'],g['MY0'],g['MX1'],g['MY1'],N,N); dst_crs=CRS.from_epsg(3857)
feats={f['id']:f for fn in ['data/stac_spring.json','data/stac_summer.json'] for f in json.load(open(fn))['features']}
def load(item,band,resamp):
    out=np.zeros((N,N),dtype=np.float32)
    with rasterio.open(item['assets'][band]['href']) as src:
        reproject(rasterio.band(src,1),out,dst_transform=dst_tr,dst_crs=dst_crs,resampling=resamp)
    return out
mode=sys.argv[1]
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_UNSAFESSL='YES',GDAL_HTTP_MAX_RETRY=4,GDAL_HTTP_RETRY_DELAY=2):
    if mode=="scl":
        for sid in sys.argv[2:]:
            s=load(feats[sid],"scl",Resampling.nearest); u,c=np.unique(s,return_counts=True)
            tot=s.size; bad=sum(cc for uu,cc in zip(u,c) if int(uu) in (0,1,3,8,9,10,11))
            print(sid,"bad%",round(100*bad/tot,2),dict(zip(u.astype(int).tolist(),c.tolist())),flush=True)
    else:
        name,sid=sys.argv[2],sys.argv[3]; item=feats[sid]; d={}
        for b in ["blue","green","red","nir","swir16","scl"]:
            d[b]=load(item,b,Resampling.nearest if b=="scl" else Resampling.bilinear); print(name,b,round(float(d[b].mean()),1),flush=True)
        d['boa_offset_applied']=np.array(bool(item['properties'].get('earthsearch:boa_offset_applied',False)))
        np.savez_compressed(f"data/s2_{name}.npz",**d)
