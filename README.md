# Quilcas Muestreo - GCBC Project

Diseño de muestreo espacial estratificado para encuesta de hogares agrícolas
en Quilcas, Huancayo, Junín, Perú.

## Descripción
Muestreo de 30 familias agricultoras alrededor de ensayos experimentales
del proyecto GCBC (Andean Crops Diversity for Climate Change).

## Estructura
- `scripts/` - Scripts de análisis en orden numérico
- `data/processed/` - Capas geoespaciales procesadas
- `outputs/` - Productos finales (muestra, KML, Excel)

## Requisitos
pip install -r requirements.txt

## Variables de entorno
Crear archivo .env con:
OPENTOPO_API_KEY=tu_key_aqui

## Flujo de análisis
00 - Crear puntos de ensayo
01 - Definir área de muestreo
02 - Descargar edificios (Google Open Buildings)
03 - Filtrar edificios
04 - Clustering
05 - Selección inicial de muestra
06 - Elevación DEM SRTM
07 - Densidad y clasificación espacial
08 - Red vial
09 - Muestra estratificada final
