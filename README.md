# Soppkart Årvoll

Et statisk nettsted som viser sannsynlighet for å finne ulike sopparter i Lillomarka ved Årvoll i Oslo. Hele siden er én selvstendig HTML-fil med kart, sannsynlighetsraster, funn og gangtid innebygd. Bare Leaflet lastes utenfra.

## Bygg siden

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python model.py
.venv/bin/python build.py
```

`model.py` tar ett til to minutter og skriver `data/model_out.json`, `data/model_png.json` og `data/grids.npz`. `build.py` setter sammen `template.html`, modellresultatet, bakgrunnskartene og Leaflet-stilarket til `site/index.html`.

## Filer

| Fil | Rolle |
| --- | --- |
| `model.py` | Bygger artsmodeller, værkalibrert fruktindeks og sannsynlighetsraster. Leser `data/`, `arvollveien.json` og `species_def.py`. |
| `build.py` | Lager `site/index.html` fra `template.html` og modellresultatet. |
| `template.html` | Selve siden. |
| `species_def.py` | Artene som modelleres, med norske og latinske navn. |
| `arvollveien.json` | Geometrien til Årvollveien fra OpenStreetMap. |
| `data/` | Ferdig beregnet grunnlag: terreng, skog, satellittindekser, GBIF-funn og værhistorikk. |

Skriptene `grid.py`, `fetch_tiles.py`, `covar.py`, `covar2.py`, `s2b.py`, `gbif_year.py` og `regional.py` er engangsskript som laget datagrunnlaget i `data/`. De ligger her som dokumentasjon og skal ikke kjøres på nytt.

## Kilder

Kartgrunnlag fra Kartverket (CC BY 4.0), skogdata fra NIBIO SR16, satellittdata fra Copernicus Sentinel-2, funn fra GBIF og Artsobservasjoner, stier fra OpenStreetMap og vær fra MET Norge via Open-Meteo og ERA5.
