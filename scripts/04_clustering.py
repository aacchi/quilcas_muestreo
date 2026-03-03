import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from pathlib import Path

DATA_DIR = Path("data/processed")

gdf = gpd.read_file(DATA_DIR / "edificios_filtrados.gpkg")
print(f"Edificios a clusterizar: {len(gdf)}")

# Convertir a UTM para trabajar en metros
gdf_utm = gdf.to_crs("EPSG:32718")
coords = np.array([[g.x, g.y] for g in gdf_utm.geometry])

# DBSCAN: eps=150m (radio), min_samples=3 (mínimo para formar clúster)
db = DBSCAN(eps=150, min_samples=3).fit(coords)
gdf["cluster"] = db.labels_

n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
n_ruido = list(db.labels_).count(-1)

print(f"\nClústeres encontrados: {n_clusters}")
print(f"Viviendas dispersas (ruido): {n_ruido}")
print(f"\nViviendas por clúster:")
resumen = gdf[gdf["cluster"] >= 0].groupby("cluster").size().reset_index(name="n_viviendas")
resumen = resumen.sort_values("n_viviendas", ascending=False)
print(resumen.to_string())

gdf.to_file(DATA_DIR / "edificios_clustered.gpkg", driver="GPKG")
resumen.to_csv(DATA_DIR / "resumen_clusters.csv", index=False)
print(f"\nGuardado: edificios_clustered.gpkg")
