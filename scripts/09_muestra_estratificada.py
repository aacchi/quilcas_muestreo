import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
import simplekml

DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

gdf = gpd.read_file(DATA_DIR / "edificios_clasificados.gpkg")
gdf_utm = gdf.to_crs("EPSG:32718")

# Estratos por densidad (radio 30m)
estratos = {
    "disperso":     {"min": 0,  "max": 2,  "n": 6},
    "semi_disperso":{"min": 3,  "max": 5,  "n": 10},
    "semi_denso":   {"min": 6,  "max": 10, "n": 9},
    "denso":        {"min": 11, "max": 99, "n": 5},
}

print("Muestreo estratificado por densidad local (radio 30m)")
print("="*55)

seleccionados = []
np.random.seed(42)  # reproducibilidad

for estrato, params in estratos.items():
    # Filtrar viviendas del estrato
    mask = (gdf["vecinos_30m"] >= params["min"]) & \
           (gdf["vecinos_30m"] <= params["max"])
    pool = gdf[mask].copy()
    n = params["n"]
    
    print(f"\nEstrato '{estrato}': {len(pool)} viviendas → seleccionar {n}")
    
    if len(pool) < n:
        print(f"  AVISO: solo hay {len(pool)} viviendas, tomamos todas")
        muestra = pool
    else:
        # Muestreo sistemático espacial dentro del estrato
        # Ordenar por latitud luego longitud para sistematicidad
        pool_sorted = pool.sort_values(["latitude", "longitude"])
        paso = len(pool_sorted) // n
        indices = [i * paso for i in range(n)]
        muestra = pool_sorted.iloc[indices]
    
    for i, (_, row) in enumerate(muestra.iterrows()):
        seleccionados.append({
            "id_encuesta": len(seleccionados) + 1,
            "estrato": estrato,
            "lat": row["latitude"],
            "lon": row["longitude"],
            "vecinos_30m": int(row["vecinos_30m"]),
            "elevacion_m": round(row.get("elevacion_m", 0), 0),
            "area_techo_m2": round(row.get("area_in_meters", 0), 1),
            "confianza": round(row.get("confidence", 0), 2),
        })

df = pd.DataFrame(seleccionados)
print(f"\n{'='*55}")
print(f"Total seleccionadas: {len(df)}")
print(f"\nResumen por estrato:")
print(df.groupby("estrato")[["lat","lon","elevacion_m","vecinos_30m"]].mean().round(2))

# ── Exportar Excel ───────────────────────────────────────────────────────────
df["instrucciones_campo"] = (
    "1. Llegar al punto GPS. "
    "2. Preguntar tamizaje: ¿Su familia cultiva alguna parcela actualmente? "
    "3. Si SÍ → aplicar encuesta. "
    "4. Si NO → ir a la vivienda más cercana visible."
)
df.to_excel(OUTPUT_DIR / "muestra_estratificada.xlsx", index=False)

# ── Exportar KML para Google My Maps ────────────────────────────────────────
kml = simplekml.Kml()

colores = {
    "disperso":      "ff0000ff",  # rojo
    "semi_disperso": "ff00ff00",  # verde
    "semi_denso":    "ffffff00",  # amarillo
    "denso":         "ffff6600",  # naranja
}

for _, row in df.iterrows():
    pnt = kml.newpoint(
        name=f"E{int(row['id_encuesta']):02d} - {row['estrato']}",
        description=(
            f"ID: {int(row['id_encuesta'])}\n"
            f"Estrato: {row['estrato']}\n"
            f"Vecinos 30m: {int(row['vecinos_30m'])}\n"
            f"Elevación: {int(row['elevacion_m'])}m\n"
            f"Techo: {row['area_techo_m2']}m²\n\n"
            f"TAMIZAJE: ¿Su familia cultiva alguna parcela actualmente?"
        ),
        coords=[(row["lon"], row["lat"])]
    )
    color = colores.get(row["estrato"], "ffffffff")
    pnt.style.iconstyle.color = color
    pnt.style.iconstyle.scale = 1.2

kml.save(str(OUTPUT_DIR / "muestra_estratificada.kml"))

# ── Exportar GeoJSON para QGIS ───────────────────────────────────────────────
features = []
for _, row in df.iterrows():
    features.append({
        "type": "Feature",
        "properties": {k: v for k, v in row.items() if k not in ["lat","lon"]},
        "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]}
    })
with open(OUTPUT_DIR / "muestra_estratificada.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

print(f"\nArchivos generados:")
print(f"  outputs/muestra_estratificada.xlsx  ← tabla de campo")
print(f"  outputs/muestra_estratificada.kml   ← Google My Maps")
print(f"  outputs/muestra_estratificada.geojson ← QGIS")
