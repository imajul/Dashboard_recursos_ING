# Simulador de Capacidad de Ingeniería

Migración del dashboard de Power BI de planificación de capacidad a una aplicación web con
simulación de recursos en vivo.

| Carpeta | Contenido |
|---|---|
| [`docs/PROPUESTA_TECNICA.md`](docs/PROPUESTA_TECNICA.md) | Propuesta técnica completa: arquitectura, modelo de datos, SharePoint, reemplazo de las tablas DAX, simulación, escenarios, viabilidad y diagramas. |
| [`prototipo/`](prototipo) | Prototipo funcional en HTML/JS: Gantt de proyectos arrastrable, matriz de ocupación con semáforo, gráfico demanda vs capacidad, edición de recursos, escenarios, comparación, exportación CSV/JSON y reporte PDF. Abrir `prototipo/index.html`. |
| [`backend/`](backend) | Motor de cálculo en Python (`app/motor.py`), API FastAPI, repositorio SQLite/SQL Server y conector SharePoint vía Microsoft Graph. |
| [`db/schema.sql`](db/schema.sql) | Modelo de datos. |
| [`data/sample_data.json`](data/sample_data.json) | Dataset de ejemplo (ilustrativo, no son datos reales). |

## Uso rápido

```bash
# Prototipo: abrir prototipo/index.html en el navegador (funciona sin servidor).

# Tests del motor, paridad Python/JavaScript y API
cd backend && python -m unittest discover -s tests -t .

# API + prototipo en http://localhost:8000  (docs en /docs)
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```
