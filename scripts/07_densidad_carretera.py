import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json

DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

gdf = gpd.read_file(DATA_DIR / "edificios_con_elevacion.gpkg")
gdf_utm = gdf.to_crs("EPSG:32718")
coords = np.array([[g.x, g.y] for g in gdf_utm.geometry])

# ── 1. Densidad local radio 30m ──────────────────────────────────────────────
print("Calculando densidad local (radio 30m)...")
densidades = []
for punto in coords:
    distancias = np.sqrt(((coords - punto)**2).sum(axis=1))
    vecinos = (distancias <= 30).sum() - 1
    densidades.append(vecinos)

gdf["vecinos_30m"] = densidades
gdf_utm["vecinos_30m"] = densidades

print(f"Media: {np.mean(densidades):.1f} vecinos | Máx: {max(densidades)}")
print(pd.cut(densidades, bins=[-1,0,2,5,10,100],
    labels=["sola","1-2","3-5","6-10",">10"]).value_counts().sort_index())

# ── 2. Distancia a carretera principal ───────────────────────────────────────
# Descargamos red vial de OSM para la zona
print("\nDescargando red vial de OSM...")
import requests

query = """
[out:json][timeout:30];
(
  way["highway"]["highway"~"primary|secondary|tertiary|unclassified|residential"]
  (-11.950,-75.280,-11.880,-75.210);
);
out geom;
"""
r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=60)
data = r.json()
print(f"Segmentos viales encontrados: {len(data['elements'])}")

# Construir geometría de carreteras
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union

lineas = []
for el in data["elements"]:
    if "geometry" in el:
        pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(pts) >= 2:
            lineas.append(LineString(pts))

if lineas:
    red_vial = gpd.GeoDataFrame(geometry=lineas, crs="EPSG:4326")
    red_vial_utm = red_vial.to_crs("EPSG:32718")
    carreteras = unary_union(red_vial_utm.geometry)

    # Distancia de cada vivienda a carretera más cercana
    print("Calculando distancia a carretera...")
    gdf_utm["dist_carretera_m"] = gdf_utm.geometry.apply(
        lambda g: g.distance(carreteras)
    )
    gdf["dist_carretera_m"] = gdf_utm["dist_carretera_m"].values

    print(f"\nDistancia a carretera:")
    print(f"  Media: {gdf['dist_carretera_m'].mean():.0f}m")
    print(f"  Máx:   {gdf['dist_carretera_m'].max():.0f}m")
    print(pd.cut(gdf["dist_carretera_m"],
        bins=[0, 50, 100, 200, 500, 9999],
        labels=["<50m","50-100m","100-200m","200-500m",">500m"]).value_counts().sort_index())

    # Guardar red vial
    red_vial.to_file(DATA_DIR / "red_vial.gpkg", driver="GPKG")

# ── 3. Clasificación combinada ───────────────────────────────────────────────
def clasificar(row):
    vecinos = row["vecinos_30m"]
    dist = row.get("dist_carretera_m", 999)
    
    if vecinos <= 2 and dist > 100:
        return "rural_disperso"      # más probable agricultor
    elif vecinos <= 5 and dist > 50:
        return "semi_rural"          # probable agricultor
    elif vecinos <= 10:
        return "nucleo_pequeno"      # puede ser agricultor
    elif dist < 50:
        return "sobre_carretera"     # riesgo comercio/transporte
    else:
        return "nucleo_denso"        # mixto

gdf["tipo_espacial"] = gdf.apply(clasificar, axis=1)

print(f"\nClasificación espacial combinada:")
print(gdf["tipo_espacial"].value_counts())

# Guardar
gdf.to_file(DATA_DIR / "edificios_clasificados.gpkg", driver="GPKG")

# Exportar resumen
resumen = gdf["tipo_espacial"].value_counts().reset_index()
resumen.columns = ["tipo", "n_viviendas"]
resumen["pct"] = (resumen["n_viviendas"] / len(gdf) * 100).round(1)
print(f"\n{resumen.to_string()}")

print(f"\nGuardado: {DATA_DIR}/edificios_clasificados.gpkg")
print("Carga en QGIS y colorea por 'tipo_espacial'")
