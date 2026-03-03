import json
from pathlib import Path

DATA_DIR = Path("data/processed")
DATA_DIR.mkdir(exist_ok=True)

features = [
    {
        "type": "Feature",
        "properties": {"name": "Pachapaqui - Drought Trial", "comunidad": "Pachapaqui"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-75.24046, -11.92777],
                [-75.24064, -11.92779],
                [-75.24062, -11.92743],
                [-75.24042, -11.92740],
                [-75.24046, -11.92777],
            ]]
        }
    },
    {
        "type": "Feature",
        "properties": {"name": "Patac - Mashua Trial", "comunidad": "Patac"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-75.25696, -11.92770],
                [-75.25690, -11.92806],
                [-75.25641, -11.92807],
                [-75.25644, -11.92768],
                [-75.25696, -11.92770],
            ]]
        }
    }
]

geojson = {"type": "FeatureCollection", "features": features}

out = DATA_DIR / "parcelas.geojson"
with open(out, "w") as f:
    json.dump(geojson, f, indent=2)

print("Parcelas creadas:")
for f in features:
    print(f"  {f['properties']['name']}")
print(f"\nGuardado: {out}")
