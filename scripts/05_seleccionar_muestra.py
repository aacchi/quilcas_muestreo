import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

gdf = gpd.read_file(DATA_DIR / "edificios_filtrados.gpkg")
print(f"Universo de viviendas: {len(gdf)}")

# Reproyectar a UTM para trabajar en metros
gdf_utm = gdf.to_crs("EPSG:32718")

# Crear grilla sobre el área y seleccionar 1 vivienda por celda
# Dividimos el área en 30 celdas y tomamos la vivienda más cercana al centro

from shapely.geometry import box
import math

# Bounding box del área
minx, miny, maxx, maxy = gdf_utm.total_bounds
ancho = maxx - minx
alto = maxy - miny
area_total = ancho * alto

# Calcular tamaño de celda para ~30 celdas
n_celdas_x = round(math.sqrt(30 * ancho / alto))
n_celdas_y = round(30 / n_celdas_x)
cell_w = ancho / n_celdas_x
cell_h = alto / n_celdas_y

print(f"Grilla: {n_celdas_x} x {n_celdas_y} = {n_celdas_x * n_celdas_y} celdas")
print(f"Tamaño de celda: {cell_w:.0f} x {cell_h:.0f} metros")

# Para cada celda, encontrar la vivienda más cercana al centroide
seleccionados = []
celda_id = 1

for i in range(n_celdas_x):
    for j in range(n_celdas_y):
        # Límites de la celda
        x0 = minx + i * cell_w
        x1 = x0 + cell_w
        y0 = miny + j * cell_h
        y1 = y0 + cell_h

        # Centroide de la celda
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2

        # Viviendas dentro de la celda
        en_celda = gdf_utm[
            (gdf_utm.geometry.x >= x0) & (gdf_utm.geometry.x <= x1) &
            (gdf_utm.geometry.y >= y0) & (gdf_utm.geometry.y <= y1)
        ]

        if len(en_celda) == 0:
            # Si no hay viviendas en la celda, tomar la más cercana al centroide
            distancias = gdf_utm.geometry.distance(
                gdf_utm.geometry.iloc[0].__class__(cx, cy)
            )
            idx = distancias.idxmin()
            vivienda = gdf_utm.loc[idx]
            nota = "más cercana (celda vacía)"
        else:
            # Tomar la más cercana al centroide dentro de la celda
            distancias = en_celda.geometry.apply(
                lambda g: ((g.x - cx)**2 + (g.y - cy)**2)**0.5
            )
            idx = distancias.idxmin()
            vivienda = en_celda.loc[idx]
            nota = f"{len(en_celda)} viviendas en celda"

        seleccionados.append({
            "id_encuesta": celda_id,
            "celda": f"{i+1}-{j+1}",
            "lat": gdf.loc[vivienda.name, "latitude"] if vivienda.name in gdf.index else vivienda.geometry.y,
            "lon": gdf.loc[vivienda.name, "longitude"] if vivienda.name in gdf.index else vivienda.geometry.x,
            "confianza": vivienda.get("confidence", ""),
            "area_techo_m2": round(vivienda.get("area_in_meters", 0), 1),
            "nota": nota
        })
        celda_id += 1

df_muestra = pd.DataFrame(seleccionados)
print(f"\nViviendas seleccionadas: {len(df_muestra)}")
print(df_muestra[["id_encuesta", "lat", "lon", "nota"]].to_string())

# Exportar Excel
df_muestra.to_excel(OUTPUT_DIR / "muestra_30_viviendas.xlsx", index=False)

# Exportar GeoJSON para QGIS
import json
features = []
for _, row in df_muestra.iterrows():
    features.append({
        "type": "Feature",
        "properties": {
            "id_encuesta": int(row["id_encuesta"]),
            "celda": row["celda"],
            "nota": row["nota"]
        },
        "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]}
    })

geojson = {"type": "FeatureCollection", "features": features}
with open(OUTPUT_DIR / "muestra_30_viviendas.geojson", "w") as f:
    json.dump(geojson, f, indent=2)

print(f"\nGuardado: outputs/muestra_30_viviendas.xlsx")
print(f"Guardado: outputs/muestra_30_viviendas.geojson")
