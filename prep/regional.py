"""Ukentlige regionale funn per art fra GBIF, til fruktindeksen. Bruk: python prep/regional.py <områdemappe>
Polygonet står i area.json som region_poly."""
import json, sys, os, time, urllib.request, urllib.parse, concurrent.futures as cf
A=sys.argv[1]; D=f"{A}/data"; os.makedirs(f"{D}/reg",exist_ok=True)
poly=json.load(open(f"{A}/area.json"))["region_poly"]; keys=json.load(open("species_keys.json"))
base="https://api.gbif.org/v1/occurrence/search?"
def get(q):
    for k in range(6):
        try: return json.load(urllib.request.urlopen(base+urllib.parse.urlencode(q,doseq=True),timeout=60))
        except Exception as e: time.sleep(3)
    return None
def part(a):
    sid,yr=a; fn=f"{D}/reg/{sid}_{yr}.json"
    if os.path.exists(fn): return
    out=[]; off=0
    while True:
        r=get(dict(taxonKey=keys[sid],geometry=poly,limit=300,offset=off,hasCoordinate="true",year=yr))
        if r is None: print("FAIL",sid,yr,flush=True); return
        out+=[(o.get('year'),o.get('month'),o.get('day')) for o in r['results']]
        if r['endOfRecords'] or off>3000: break
        off+=300
    json.dump(out,open(fn,'w'))
jobs=[(s,y) for s in keys if s!="flatklokke" for y in range(2008,2026)]
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(part,jobs))
print("reg files",len(os.listdir(f"{D}/reg")),flush=True)
