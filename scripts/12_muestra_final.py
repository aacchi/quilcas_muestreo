import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
import simplekml
import math
import rasterio
import pyproj

DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

np.random.seed(42)

DIST_MINIMA = 200  # metros entre puntos seleccionados

# Transformer WGS84 -> UTM 18S
transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32718", always_xy=True)

predios = gpd.read_file(DATA_DIR / "predios_limpios.gpkg")
predios_utm = predios.to_crs("EPSG:32718")

print(f"Universo: {len(predios)} predios (filtrado area <= 500m2)")
print(predios["piso"].value_counts())
print(f"\nDistancia minima entre puntos: {DIST_MINIMA}m")

asignacion = {"quechua_alto": 18, "suni_bajo": 12}

seleccionados = []
seleccionados_utm = []  # coordenadas UTM de puntos ya elegidos

for piso, n_objetivo in asignacion.items():
    estrato = predios[predios["piso"] == piso].copy()
    estrato_utm = predios_utm[predios["piso"] == piso].copy()

    print(f"\nMuestreando {piso}: {len(estrato)} predios -> {n_objetivo}")

    minx, miny, maxx, maxy = estrato_utm.total_bounds
    ancho = maxx - minx
    alto  = maxy - miny
    ratio = ancho / alto if alto > 0 else 1
    n_cols = max(1, round(math.sqrt(n_objetivo * ratio)))
    n_rows = max(1, round(n_objetivo / n_cols))
    while n_cols * n_rows < n_objetivo:
        n_cols += 1

    cell_w = ancho / n_cols
    cell_h = alto  / n_rows

    usados = set()
    n_sel = 0

    celdas = [
        (minx + (col+0.5)*cell_w, miny + (row+0.5)*cell_h, col, row)
        for col in range(n_cols)
        for row in range(n_rows)
    ]

    for cx, cy, col, row in celdas:
        if n_sel >= n_objetivo:
            break

        x0 = minx + col * cell_w
        x1 = minx + (col+1) * cell_w
        y0 = miny + row * cell_h
        y1 = miny + (row+1) * cell_h

        en_celda_mask = (
            (estrato_utm.geometry.x >= x0) & (estrato_utm.geometry.x < x1) &
            (estrato_utm.geometry.y >= y0) & (estrato_utm.geometry.y < y1)
        )
        candidatos = estrato_utm[en_celda_mask & ~estrato_utm.index.isin(usados)]

        if len(candidatos) == 0:
            candidatos = estrato_utm[~estrato_utm.index.isin(usados)]
            if len(candidatos) == 0:
                continue

        # Ordenar por distancia al centroide
        dists_c = candidatos.geometry.apply(
            lambda g: math.sqrt((g.x-cx)**2 + (g.y-cy)**2)
        ).sort_values()

        # Elegir el mas cercano que respete distancia minima (en UTM)
        elegido = None
        for idx in dists_c.index:
            g = estrato_utm.loc[idx].geometry
            punto_utm = np.array([g.x, g.y])

            demasiado_cerca = False
            for sc_utm in seleccionados_utm:
                if np.sqrt(((punto_utm - sc_utm)**2).sum()) < DIST_MINIMA:
                    demasiado_cerca = True
                    break

            if not demasiado_cerca:
                elegido = idx
                break

        if elegido is None:
            # Tomar el que maximiza distancia minima a puntos ya seleccionados
            if seleccionados_utm:
                mejor_dist = -1
                for idx in dists_c.index:
                    g = estrato_utm.loc[idx].geometry
                    p = np.array([g.x, g.y])
                    dist_min = min(np.sqrt(((p - sc)**2).sum()) for sc in seleccionados_utm)
                    if dist_min > mejor_dist:
                        mejor_dist = dist_min
                        elegido = idx
            else:
                elegido = dists_c.index[0]
            print(f"  Aviso: celda {col+1}-{row+1} relaja distancia minima ({mejor_dist:.0f}m)")

        usados.add(elegido)
        v = estrato.loc[elegido]
        g_utm = estrato_utm.loc[elegido].geometry
        seleccionados_utm.append(np.array([g_utm.x, g_utm.y]))
        n_sel += 1

        # Reemplazos: 2 predios mas cercanos no usados
        disponibles = estrato_utm[~estrato_utm.index.isin(usados)]
        dists_r = disponibles.geometry.apply(
            lambda g: math.sqrt((g.x-g_utm.x)**2 + (g.y-g_utm.y)**2)
        ).sort_values()

        r1 = estrato.loc[dists_r.index[0]] if len(dists_r) > 0 else None
        r2 = estrato.loc[dists_r.index[1]] if len(dists_r) > 1 else None

        seleccionados.append({
            "id_encuesta":    len(seleccionados) + 1,
            "piso":           piso,
            "lat":            float(v["latitude"]),
            "lon":            float(v["longitude"]),
            "elevacion_m":    int(v.get("elevacion_m", 0)),
            "n_techos":       int(v.get("n_techos", 1)),
            "area_total_m2":  round(float(v.get("area_total_m2", 0)), 1),
            "reemplazo1_lat": float(r1["latitude"]) if r1 is not None else "",
            "reemplazo1_lon": float(r1["longitude"]) if r1 is not None else "",
            "reemplazo2_lat": float(r2["latitude"]) if r2 is not None else "",
            "reemplazo2_lon": float(r2["longitude"]) if r2 is not None else "",
        })

df = pd.DataFrame(seleccionados)
df = df.sort_values("lat", ascending=True).reset_index(drop=True)
df["orden_visita"] = df.index + 1

print(f"\n{'='*50}")
print(f"MUESTRA FINAL: {len(df)} predios")
print(df["piso"].value_counts())
print(f"Elevacion: {df['elevacion_m'].min()}m - {df['elevacion_m'].max()}m")

# Verificar distancias reales en UTM
coords_utm_final = np.array([
    transformer.transform(r["lon"], r["lat"])
    for _, r in df.iterrows()
])
dist_min_real = []
for i, p in enumerate(coords_utm_final):
    otros = np.delete(coords_utm_final, i, axis=0)
    dist_min_real.append(np.sqrt(((otros - p)**2).sum(axis=1)).min())

print(f"\nDistancia minima real entre puntos: {min(dist_min_real):.0f}m")
print(f"Distancia media entre puntos: {np.mean(dist_min_real):.0f}m")

# Columnas de campo
df["encuestador"]       = ""
df["fecha"]             = ""
df["hora_llegada"]      = ""
df["tamizaje_cultiva"]  = ""
df["encuesta_aplicada"] = ""
df["motivo_rechazo"]    = ""
df["observaciones"]     = ""

cols = [
    "orden_visita","id_encuesta","piso","lat","lon","elevacion_m",
    "n_techos","area_total_m2",
    "reemplazo1_lat","reemplazo1_lon","reemplazo2_lat","reemplazo2_lon",
    "encuestador","fecha","hora_llegada",
    "tamizaje_cultiva","encuesta_aplicada","motivo_rechazo","observaciones"
]
df[cols].to_excel(OUTPUT_DIR / "muestra_final.xlsx", index=False)

# KML
kml = simplekml.Kml()
colores_piso = {"quechua_alto": "ff00cc00", "suni_bajo": "ff0066ff"}
for _, row in df.iterrows():
    pnt = kml.newpoint(
        name=f"V{int(row['orden_visita']):02d} | {row['piso']}",
        description=(
            f"Orden: {int(row['orden_visita'])}\n"
            f"Piso: {row['piso']}\n"
            f"Elevacion: {int(row['elevacion_m'])}m\n"
            f"Techos en predio: {int(row['n_techos'])}\n\n"
            f"REEMPLAZO 1: {row['reemplazo1_lat']}, {row['reemplazo1_lon']}\n"
            f"REEMPLAZO 2: {row['reemplazo2_lat']}, {row['reemplazo2_lon']}\n\n"
            f"TAMIZAJE: Su familia cultiva alguna parcela?\n"
            f"[ ] SI -> encuestar\n"
            f"[ ] NO -> ir a Reemplazo 1"
        ),
        coords=[(row["lon"], row["lat"])]
    )
    pnt.style.iconstyle.color = colores_piso.get(row["piso"], "ffffffff")
    pnt.style.iconstyle.scale = 1.3

kml.save(str(OUTPUT_DIR / "muestra_final.kml"))

# GeoJSON
features = []
for _, row in df.iterrows():
    features.append({
        "type": "Feature",
        "properties": {
            "orden_visita": int(row["orden_visita"]),
            "id_encuesta":  int(row["id_encuesta"]),
            "piso":         row["piso"],
            "elevacion_m":  int(row["elevacion_m"]),
            "n_techos":     int(row["n_techos"]),
        },
        "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]}
    })

with open(OUTPUT_DIR / "muestra_final.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

print(f"\nGuardado: muestra_final.xlsx | muestra_final.kml | muestra_final.geojson")
