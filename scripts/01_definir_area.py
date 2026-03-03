import folium
from pathlib import Path

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

ensayos = {
    "Drought Trial - Quilcas": (-11.9056, -75.2401),
    "Mashua Trial - Quilcas":  (-11.9194, -75.2480),
}

poligono_drought = [
    (-11.92777, -75.24046),
    (-11.92779, -75.24064),
    (-11.92743, -75.24062),
    (-11.92740, -75.24042),
]

area_muestreo = [
    (-11.895, -75.260),
    (-11.895, -75.230),
    (-11.935, -75.225),
    (-11.940, -75.260),
    (-11.920, -75.270),
]

centro = (-11.915, -75.248)
mapa = folium.Map(location=centro, zoom_start=14, tiles="Esri.WorldImagery")

for nombre, (lat, lon) in ensayos.items():
    folium.Marker(
        location=[lat, lon],
        popup=nombre,
        tooltip=nombre,
        icon=folium.Icon(color="red", icon="leaf", prefix="fa"),
    ).add_to(mapa)

folium.Polygon(
    locations=poligono_drought,
    color="yellow", weight=2, fill=True, fill_opacity=0.3,
    tooltip="Predio Drought Trial",
).add_to(mapa)

folium.Polygon(
    locations=area_muestreo,
    color="cyan", weight=3, fill=True, fill_opacity=0.15,
    tooltip="Area de muestreo propuesta",
).add_to(mapa)

localidades = {
    "Colpar":      (-11.898, -75.258),
    "Patac":       (-11.918, -75.255),
    "C.P. Llacta": (-11.925, -75.245),
    "Quilcas":     (-11.930, -75.238),
    "Pirsinio":    (-11.928, -75.228),
}

for nombre, (lat, lon) in localidades.items():
    folium.Marker(
        location=[lat, lon],
        tooltip=nombre,
        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
    ).add_to(mapa)

output_path = OUTPUT_DIR / "01_area_muestreo.html"
mapa.save(str(output_path))
print(f"Mapa guardado: {output_path}")
print("Abrelo con: start outputs/01_area_muestreo.html")
