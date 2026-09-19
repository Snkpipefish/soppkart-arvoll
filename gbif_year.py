import json, urllib.request, urllib.parse, concurrent.futures as cf, time, os
poly="POLYGON((10.7776 59.9385,10.8765 59.9385,10.8765 59.9880,10.7776 59.9880,10.7776 59.9385))"
base="https://api.gbif.org/v1/occurrence/search?"
keep=("speciesKey","species","decimalLatitude","decimalLongitude","coordinateUncertaintyInMeters","eventDate","year","month","day","datasetKey")
def get(q):
    for k in range(6):
        try: return json.load(urllib.request.urlopen(base+urllib.parse.urlencode(q),timeout=60))
        except Exception as e: time.sleep(3)
    return None
def part(yr):
    fn=f"data/gbif_pages/{yr}.json"
    if os.path.exists(fn): return
    out=[]; off=0
    while True:
        r=get(dict(kingdomKey=5,geometry=poly,limit=300,offset=off,hasCoordinate="true",year=yr))
        if r is None: print("FAIL",yr,off,flush=True); return
        out+= [{k:o.get(k) for k in keep} for o in r['results']]
        if r['endOfRecords']: break
        off+=300
    json.dump(out,open(fn,'w')); print(yr,len(out),flush=True)
parts=["1700,1989","1990,1999","2000,2004","2005,2008"]+[str(y) for y in range(2009,2027)]
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(part,parts))
print("DONE",flush=True)
