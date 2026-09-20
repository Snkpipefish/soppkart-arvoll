# Soppkart

Statiske nettsider som viser sannsynlighet for å finne ulike sopparter i skogen innen gangavstand fra et utgangspunkt. Hver side er én selvstendig HTML-fil med kart, sannsynlighetsraster, funn og gangtid innebygd. Bare Leaflet lastes utenfra.

| Område | Utgangspunkt | Side |
| --- | --- | --- |
| Årvoll, Oslo | Årvollveien | `site/index.html` |
| Skarnes, Sør-Odal | Spiksetsvingen | `site/skarnes/index.html` |

## Bygg sidene

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python model.py areas/arvoll
.venv/bin/python model.py areas/skarnes
.venv/bin/python build.py
```

`model.py` tar ett til to minutter per område og skriver `model_out.json`, `model_png.json` og `grids.npz` i områdets `data/`. `build.py` setter sammen `template.html`, modellresultatet, bakgrunnskartene og Leaflet-stilarket til `site/<sti>/index.html` for hvert område.

## Filer

| Fil | Rolle |
| --- | --- |
| `model.py` | Bygger artsmodeller, værkalibrert fruktindeks og sannsynlighetsraster for ett område. |
| `build.py` | Lager HTML-sidene fra `template.html` og modellresultatene. |
| `template.html` | Selve siden. Plassholdere som `{{road}}` fylles av `build.py`. |
| `species_def.py` | Artene som modelleres, med norske og latinske navn. |
| `species_keys.json` | GBIF-taksonnøkler for artene. |
| `areas/<id>/area.json` | Områdets navn, utgangspunkt, værpunkt, region og tekster. |
| `areas/<id>/data/` | Ferdig beregnet grunnlag: terreng, skog, satellittindekser, GBIF-funn og værhistorikk. |
| `assets/leaflet.css` | Leaflet-stilark som bygges inn i siden. |

## Nytt område

Skriptene i `prep/` henter og beregner datagrunnlaget for et nytt område. De trenger `rasterio` og `pyproj` i tillegg til pakkene i `requirements.txt`.

```bash
# 1. Lag areas/<id>/area.json og hent veien som utgangspunkt fra Overpass til areas/<id>/<road_file>
# 2. Rutenett, gråtonekart, terrengmodell, SR16, Sentinel-2-metadata og GBIF-funn
.venv/bin/python prep/fetch_area.py areas/<id> <lon_vest> <lat_nord> <vårscene> <høstscene>
# 3. OSM-stier og arealbruk, regionale ukefunn: se prep/fetch_area.py og regional.py for spørringene
.venv/bin/python prep/terrain.py areas/<id>
.venv/bin/python prep/s2.py areas/<id> load spring <vårscene>
.venv/bin/python prep/s2.py areas/<id> load late <høstscene>
.venv/bin/python prep/covars.py areas/<id>
.venv/bin/python prep/weather.py areas/<id>
```

Skriptene `grid.py`, `fetch_tiles.py`, `covar.py`, `covar2.py`, `s2b.py`, `gbif_year.py` og `regional.py` er de opprinnelige engangsskriptene som laget grunnlaget for Årvoll. De ligger her som dokumentasjon og skal ikke kjøres på nytt. `prep/` er parametriserte utgaver av de samme skriptene.

## Publisering

GitHub Actions kjører modellen og bygger sidene ved hver push til `main`, og publiserer `site/` til GitHub Pages.

## Kilder

Kartgrunnlag fra Kartverket (CC BY 4.0), høydedata fra Kartverket, skogdata fra NIBIO SR16, satellittdata fra Copernicus Sentinel-2, funn fra GBIF og Artsobservasjoner, stier fra OpenStreetMap og vær fra MET Norge via Open-Meteo og ERA5.
