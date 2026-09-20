"""Henter værhistorikk (ERA5) og varsel (MET Norge via Open-Meteo) for et område. Bruk: python prep/weather.py <områdemappe>"""
import sys, json, time, datetime as dt, urllib.request
A=sys.argv[1]; D=f"{A}/data"; a=json.load(open(f"{A}/area.json")); lat,lon=a["weather_point"]
today=dt.date.today().isoformat(); V="precipitation_sum,temperature_2m_mean,temperature_2m_min,et0_fao_evapotranspiration"
def get(u):
    for k in range(5):
        try: return json.load(urllib.request.urlopen(u,timeout=120))
        except Exception as e: err=e; time.sleep(5)
    raise err
arch=get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2007-10-01&end_date={today}&daily={V}&timezone=Europe%2FOslo")
fc=get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&past_days=72&forecast_days=7&daily={V}&timezone=Europe%2FOslo")
fc["fetched"]=today
json.dump(arch,open(f"{D}/weather_archive.json","w")); json.dump(fc,open(f"{D}/weather.json","w"))
print(A,"fetched",today,"archive to",arch["daily"]["time"][-1],"forecast",fc["daily"]["time"][0],"to",fc["daily"]["time"][-1])
