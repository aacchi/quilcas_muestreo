# 02_descargar_edificios.py
# Descarga edificios desde Google Open Buildings v3
# Tile 911 = Junín, Perú

import pandas as pd
import geopandas as gpd
from pathlib import Path

OUTPUT_DIR = Path("outputs")
DATA_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Área de interés (Quilcas, Huancayo)
WEST, SOUTH, EAST, NORTH = -75.270, -11.940, -75.220, -11.890

# Tile correcto para Junín (calculado con s2sphere)
TILE_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/911_buildings.csv.gz"

print("Descargando tile 911 (Junín, Perú)...")
print("Esto puede tomar 2-3 minutos...")

df = pd.read_csv(TILE_URL, compression="gzip")
print(f"Total en tile: {len(df):,}")

# Filtrar por bounding box
df_zona = df[
    (df["latitude"]  >= SOUTH) & (df["latitude"]  <= NORTH) &
    (df["longitude"] >= WEST)  & (df["longitude"] <= EAST)
].copy()

print(f"Edificios en zona Quilcas: {len(df_zona)}")
print(f"Confianza promedio: {df_zona['confidence'].mean():.2f}")
print(f"Área promedio de techo: {df_zona['area_in_meters'].mean():.1f} m2")

# Convertir a GeoDataFrame
gdf = gpd.GeoDataFrame(
    df_zona,
    geometry=gpd.points_from_xy(df_zona["longitude"], df_zona["latitude"]),
    crs="EPSG:4326"
)

# Guardar
gdf.to_file(DATA_DIR / "edificios.gpkg", driver="GPKG")
df_zona.to_csv(DATA_DIR / "edificios.csv", index=False)

print(f"\nGuardado: {DATA_DIR}/edificios.gpkg")
print(f"Guardado: {DATA_DIR}/edificios.csv")
print("SIGUIENTE: python scripts/03_filtrar_edificios.py")
