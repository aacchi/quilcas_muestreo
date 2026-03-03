import os
import rasterio
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
import requests
import zipfile
import io

DATA_DIR = Path("data/raw")
PROC_DIR = Path("data/processed")
DATA_DIR.mkdir(exist_ok=True)

# Descarga DEM SRTM 30m desde OpenTopography
# Bounding box: Quilcas y alrededores
WEST, SOUTH, EAST, NORTH = -75.280, -11.950, -75.210, -11.880

print("Descargando DEM SRTM (30m) para Quilcas...")

url = (
    "https://portal.opentopography.org/API/globaldem?"
    f"demtype=SRTMGL1&"
    f"south={SOUTH}&north={NORTH}&west={WEST}&east={EAST}&"
f"outputFormat=GTiff&API_Key={os.environ.get('OPENTOPO_API_KEY','')}"
"
)

r = requests.get(url, timeout=60)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    dem_path = DATA_DIR / "dem_quilcas.tif"
    with open(dem_path, "wb") as f:
        f.write(r.content)
    print(f"DEM guardado: {dem_path}")

    # Leer DEM y extraer elevación para cada vivienda
    gdf = gpd.read_file(PROC_DIR / "edificios_filtrados.gpkg")

    with rasterio.open(dem_path) as src:
        print(f"Resolución: {src.res[0]*111000:.0f}m x {src.res[1]*111000:.0f}m")
        print(f"Rango altitudinal del área: verificando...")

        coords = [(g.x, g.y) for g in gdf.geometry]
        elevaciones = [v[0] for v in src.sample(coords)]
        gdf["elevacion_m"] = elevaciones

    print(f"\nElevación en el área:")
    print(f"  Mínima: {gdf['elevacion_m'].min():.0f} m")
    print(f"  Máxima: {gdf['elevacion_m'].max():.0f} m")
    print(f"  Media:  {gdf['elevacion_m'].mean():.0f} m")
    print(f"  Rango:  {gdf['elevacion_m'].max() - gdf['elevacion_m'].min():.0f} m")

    # Clasificar por piso agroecológico
    # Ajustar estos rangos según conocimiento local
    def clasificar_piso(elev):
        if elev < 3400:
            return "quechua_bajo"
        elif elev < 3600:
            return "quechua_medio"
        elif elev < 3800:
            return "quechua_alto"
        else:
            return "suni"

    gdf["piso_agroecologico"] = gdf["elevacion_m"].apply(clasificar_piso)

    print(f"\nViviendas por piso agroecológico:")
    print(gdf["piso_agroecologico"].value_counts())

    gdf.to_file(PROC_DIR / "edificios_con_elevacion.gpkg", driver="GPKG")
    print(f"\nGuardado: {PROC_DIR}/edificios_con_elevacion.gpkg")
    print("SIGUIENTE: cargar en QGIS y colorear por piso")

else:
    print(f"Error: {r.text[:300]}")
    print("Prueba registrarte en opentopography.org para obtener API key")
