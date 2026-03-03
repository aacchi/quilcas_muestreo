import geopandas as gpd
import requests
import numpy as np
import pandas as pd
from shapely.geometry import LineString
from shapely.ops import unary_union
from pathlib import Path

DATA_DIR = Path("data/processed")

# Solo vías principales
print("Descargando solo vías principales...")
query = """
[out:json][timeout:30];
(
  way["highway"~"primary|secondary|tertiary"]
  (-11.950,-75.280,-11.880,-75.210);
);
out geom;
"""
r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=60)
data = r.json()
print(f"Segmentos principales encontrados: {len(data['elements'])}")

lineas = []
for el in data["elements"]:
    if "geometry" in el:
        pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(pts) >= 2:
            lineas.append({
                "highway": el["tags"].get("highway",""),
                "name": el["tags"].get("name",""),
                "geometry": LineString(pts)
            })

red_principal = gpd.GeoDataFrame(lineas, crs="EPSG:4326")
red_principal_utm = red_principal.to_crs("EPSG:32718")
carreteras = unary_union(red_principal_utm.geometry)

print(f"\nVías por tipo:")
print(red_principal["highway"].value_counts())
print(f"\nNombres: {red_principal['name'].unique()}")

# Recalcular distancias
gdf = gpd.read_file(DATA_DIR / "edificios_clasificados.gpkg")
gdf_utm = gdf.to_crs("EPSG:32718")

print("\nCalculando distancia a vías principales...")
gdf["dist_via_principal_m"] = gdf_utm.geometry.apply(
    lambda g: g.distance(carreteras)
)

print(f"\nDistancia a vía principal:")
print(f"  Media: {gdf['dist_via_principal_m'].mean():.0f}m")
print(f"  Máx:   {gdf['dist_via_principal_m'].max():.0f}m")
print(pd.cut(gdf["dist_via_principal_m"],
    bins=[0, 50, 100, 200, 500, 9999],
    labels=["<50m","50-100m","100-200m","200-500m",">500m"]
).value_counts().sort_index())

# Reclasificar con nueva distancia
def clasificar(row):
    vecinos = row["vecinos_30m"]
    dist = row["dist_via_principal_m"]
    if vecinos <= 2 and dist > 200:
        return "rural_disperso"
    elif vecinos <= 5 and dist > 100:
        return "semi_rural"
    elif dist < 50 and vecinos > 10:
        return "sobre_via_principal"
    elif vecinos <= 10:
        return "nucleo_rural"
    else:
        return "nucleo_denso"

gdf["tipo_espacial_v2"] = gdf.apply(clasificar, axis=1)
print(f"\nClasificación revisada:")
print(gdf["tipo_espacial_v2"].value_counts())

red_principal.to_file(DATA_DIR / "red_vial_principal.gpkg", driver="GPKG")
gdf.to_file(DATA_DIR / "edificios_clasificados.gpkg", driver="GPKG")
print(f"\nGuardado: red_vial_principal.gpkg y edificios_clasificados.gpkg")
# CORRECCIÓN: incluir unclassified, excluir residential
