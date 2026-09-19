import json, urllib.request, urllib.parse, concurrent.futures as cf, time, os
keys=json.load(open('data/species_keys.json'))
poly="POLYGON((10.35 59.75,11.25 59.75,11.25 60.20,10.35 60.20,10.35 59.75))"
base="https://api.gbif.org/v1/occurrence/search?"
def get(q):
    for k in range(6):
        try: return json.load(urllib.request.urlopen(base+urllib.parse.urlencode(q,doseq=True),timeout=60))
        except Exception as e: time.sleep(3)
    return None
def part(a):
    sid,yr=a; fn=f"data/reg/{sid}_{yr}.json"
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
# archive weather first
u="https://archive-api.open-meteo.com/v1/archive?latitude=59.962&longitude=10.825&start_date=2007-10-01&end_date=2026-09-14&daily=precipitation_sum,temperature_2m_mean,temperature_2m_min,et0_fao_evapotranspiration&timezone=Europe%2FOslo"
for k in range(4):
    try:
        open('data/weather_archive.json','wb').write(urllib.request.urlopen(u,timeout=120).read()); print("archive ok",flush=True); break
    except Exception as e: print("archive retry",e,flush=True); time.sleep(5)
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(part,jobs))
print("DONE",flush=True)
