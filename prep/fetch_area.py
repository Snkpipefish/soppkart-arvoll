"""Henter datagrunnlag for et nytt område: rutenett, gråtonekart, terrengmodell, SR16, Sentinel-2-metadata og GBIF-funn.
Bruk: python prep/fetch_area.py <områdemappe> <lon_vest> <lat_nord> [spring_scene late_scene]
Rutenettet blir 9x9 WMTS-fliser på zoomnivå 15 (ca. 5,5 km) med nordvesthjørnet i angitt punkt."""
import sys, os, math, json, io, time, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image
A=sys.argv[1]; LON_W=float(sys.argv[2]); LAT_N=float(sys.argv[3]); D=f"{A}/data"; os.makedirs(f"{D}/tiles",exist_ok=True); os.makedirs(f"{D}/gbif_pages",exist_ok=True)
Z=15; R=6378137.0; NT=9
def ll2tile(lat,lon,z):
    n=2**z; return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
def tile2merc(tx,ty,z):
    n=2**z; return (tx/n*2-1)*math.pi*R,(1-ty/n*2)*math.pi*R
def merc2ll(mx,my): return math.degrees(2*math.atan(math.exp(my/R))-math.pi/2),math.degrees(mx/R)
x,y=ll2tile(LAT_N,LON_W,Z); TX0,TY0=int(math.floor(x)),int(math.floor(y)); TX1,TY1=TX0+NT-1,TY0+NT-1
MX0,MY1=tile2merc(TX0,TY0,Z); MX1,MY0=tile2merc(TX1+1,TY1+1,Z)
g=dict(Z=Z,TX0=TX0,TX1=TX1,TY0=TY0,TY1=TY1,MX0=MX0,MY0=MY0,MX1=MX1,MY1=MY1,SW=merc2ll(MX0,MY0),NE=merc2ll(MX1,MY1))
json.dump(g,open(f"{D}/grid.json","w")); print("grid",g["SW"],g["NE"],flush=True)
UA={"User-Agent":"soppkart/1.0"}
def get(url,data=None,tries=6,timeout=120):
    for k in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url,data=data,headers=UA),timeout=timeout).read()
        except Exception as e: err=e; time.sleep(3*(k+1))
    raise err
STEPS=set(os.environ.get("STEPS","tiles,dtm,sr16,stac,gbif").split(","))
# --- gråtonekart fra Kartverket WMTS
def tile(t):
    tx,ty=t; fn=f"{D}/tiles/topograatone_{tx}_{ty}.png"
    if not(os.path.exists(fn) and os.path.getsize(fn)>500): open(fn,"wb").write(get(f"https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{Z}/{ty}/{tx}.png"))
    return fn
ts=[(tx,ty) for tx in range(TX0,TX1+1) for ty in range(TY0,TY1+1)]
if "tiles" in STEPS:
    with cf.ThreadPoolExecutor(2) as ex: fns=list(ex.map(tile,ts))
    im=Image.new("RGB",(NT*256,NT*256),(255,255,255))
    for (tx,ty),fn in zip(ts,fns): im.paste(Image.open(fn).convert("RGB"),((tx-TX0)*256,(ty-TY0)*256))
    im.save(f"{D}/base_grey.jpg",quality=82); print("base_grey",im.size,flush=True)
# --- terrengmodell 5 m i UTM33 fra hoydedata.no
from pyproj import Transformer
if "dtm" in STEPS:
  t=Transformer.from_crs(3857,25833,always_xy=True)
  cx=[MX0,MX1,MX1,MX0]; cy=[MY0,MY0,MY1,MY1]; ux,uy=t.transform(cx,cy)
  x0,x1,y0,y1=math.floor(min(ux)/5)*5-100,math.ceil(max(ux)/5)*5+100,math.floor(min(uy)/5)*5-100,math.ceil(max(uy)/5)*5+100
  W,H=int((x1-x0)/5),int((y1-y0)/5)
  q=dict(bbox=f"{x0},{y0},{x1},{y1}",bboxSR=25833,imageSR=25833,size=f"{W},{H}",format="tiff",pixelType="F32",interpolation="RS_BilinearInterpolation",f="image")
  open(f"{D}/dtm_utm33_5m.tif","wb").write(get("https://hoydedata.no/arcgis/rest/services/DTM/ImageServer/exportImage?"+urllib.parse.urlencode(q),timeout=300))
  import rasterio
  with rasterio.open(f"{D}/dtm_utm33_5m.tif") as ds: a=ds.read(1); print("dtm",ds.bounds,ds.res,a.shape,"min/max",float(a.min()),float(a.max()),flush=True)
# --- SR16 fra NIBIO WMS, 1152 px i EPSG:3857
for lay in (("SRRTRESLAG","SRRBONITET","SRRHOYDEM","SRRKRONEDEK","SRRVOLMB") if "sr16" in STEPS else ()):
    u=f"https://wms.nibio.no/cgi-bin/sr16?service=WMS&version=1.3.0&request=GetMap&layers={lay}&styles=&crs=EPSG:3857&bbox={MX0},{MY0},{MX1},{MY1}&width=1152&height=1152&format=image/png&transparent=true"
    open(f"{D}/sr16_{lay}.png","wb").write(get(u,timeout=300))
    im=Image.open(f"{D}/sr16_{lay}.png").convert("RGBA"); cols=im.getcolors(1<<20); print(lay,im.size,sorted(cols,reverse=True)[:12],flush=True)
# --- Sentinel-2-scener (STAC-elementer med assets)
if len(sys.argv)>5 and "stac" in STEPS:
    for name,sid in (("spring",sys.argv[4]),("summer",sys.argv[5])):
        it=json.loads(get(f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{sid}"))
        json.dump(dict(features=[it]),open(f"{D}/stac_{name}.json","w")); print("stac",name,it["id"],it["properties"]["datetime"][:10],flush=True)
# --- GBIF: alle soppfunn innenfor rutenettet
sw,ne=g["SW"],g["NE"]; poly=f"POLYGON(({sw[1]} {sw[0]},{ne[1]} {sw[0]},{ne[1]} {ne[0]},{sw[1]} {ne[0]},{sw[1]} {sw[0]}))"
keep=("speciesKey","species","decimalLatitude","decimalLongitude","coordinateUncertaintyInMeters","eventDate","year","month","day","datasetKey")
def part(yr):
    fn=f"{D}/gbif_pages/{yr}.json"
    if os.path.exists(fn): return
    out=[]; off=0
    while True:
        r=json.loads(get("https://api.gbif.org/v1/occurrence/search?"+urllib.parse.urlencode(dict(kingdomKey=5,geometry=poly,limit=300,offset=off,hasCoordinate="true",year=yr)),tries=6))
        out+=[{k:o.get(k) for k in keep} for o in r["results"]]
        if r["endOfRecords"]: break
        off+=300
    json.dump(out,open(fn,"w"))
if "gbif" not in STEPS: sys.exit(0)
parts=["1700,1989","1990,1999","2000,2004","2005,2008"]+[str(y) for y in range(2009,2027)]
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(part,parts))
recs=[r for p in parts for r in json.load(open(f"{D}/gbif_pages/{p}.json"))]
json.dump(recs,open(f"{D}/gbif_all.json","w")); print("gbif records",len(recs),flush=True)
