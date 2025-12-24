# Roblox Insights - Stepford County Railway

Sistema ligero para recopilar datos reales del juego **Stepford County Railway** en Roblox, almacenar snapshots en segundo plano y generar predicciones de milestones de visitas.

## Requisitos

- Python 3.11+

## Instalación rápida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar el backend

```bash
uvicorn app.main:app --reload
```

El sistema levantará un colector en segundo plano que actualiza los datos cada 5 minutos. La interfaz web vive en `http://localhost:8000/`.

## Endpoints útiles

- `GET /api/latest`: último snapshot (visitas, likes, jugadores, etc.)
- `GET /api/milestones`: milestones alcanzados y predicciones
- `GET /api/prediction`: predicción del siguiente milestone
- `GET /api/versions`: historial de versiones detectadas en el título

## Configuración rápida

Puedes ajustar el intervalo de recolección o el tamaño de milestone en `app/settings.py`.
