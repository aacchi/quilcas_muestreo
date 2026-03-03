import geopandas as gpd
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

gdf = gpd.read_file(DATA_DIR / "edificios.gpkg")
print(f"Total edificios descargados: {len(gdf)}")

# Filtros más inclusivos para zona andina rural
# Confianza >= 0.60 (antes 0.65)
# Área >= 10 m2 (antes 20) - techos pequeños son comunes
# Área <= 600 m2 (antes 500)
gdf_filtrado = gdf[
    (gdf['confidence'] >= 0.60) &
    (gdf['area_in_meters'] >= 10) &
    (gdf['area_in_meters'] <= 600)
].copy()

print(f"Después de filtrar: {len(gdf_filtrado)}")

# Recortar por polígono de muestreo
area = gpd.read_file(DATA_DIR / "area_muestreo.shp")
area = area.to_crs("EPSG:4326")

gdf_dentro = gpd.sjoin(gdf_filtrado, area, how="inner", predicate="within")
print(f"Edificios dentro del área de muestreo: {len(gdf_dentro)}")

# Ver cuántos quedan en zona Colpar
colpar_check = gdf_dentro[
    (gdf_dentro['latitude'] >= -11.915) & (gdf_dentro['latitude'] <= -11.900)
]
print(f"De esos, en zona Colpar/Llacta: {len(colpar_check)}")

gdf_dentro.to_file(DATA_DIR / "edificios_filtrados.gpkg", driver="GPKG")
print(f"\nGuardado: {DATA_DIR}/edificios_filtrados.gpkg")
