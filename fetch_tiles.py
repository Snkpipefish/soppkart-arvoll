import urllib.request, os, sys, concurrent.futures as cf
from grid import *
from PIL import Image
import io
layer=sys.argv[1]
def get(t):
    tx,ty=t
    fn=f"tiles/{layer}_{tx}_{ty}.png"
    if os.path.exists(fn) and os.path.getsize(fn)>500: return fn
    url=f"https://cache.kartverket.no/v1/wmts/1.0.0/{layer}/default/webmercator/{Z}/{ty}/{tx}.png"
    req=urllib.request.Request(url,headers={"User-Agent":"soppkart-arvoll/1.0"})
    for i in range(3):
        try:
            b=urllib.request.urlopen(req,timeout=30).read(); open(fn,'wb').write(b); return fn
        except Exception as e: err=e
    print("FAIL",url,err); return None
ts=[(x,y) for x in range(TX0,TX1+1) for y in range(TY0,TY1+1)]
with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(get,ts))
W,H=NX*256,NY*256
im=Image.new("RGB",(W,H),(255,255,255))
for (tx,ty),fn in zip(ts,res):
    if fn: im.paste(Image.open(fn).convert("RGB"),((tx-TX0)*256,(ty-TY0)*256))
im.save(f"data/base_{layer}.png"); print(layer,im.size,sum(1 for r in res if r),"tiles ok")
