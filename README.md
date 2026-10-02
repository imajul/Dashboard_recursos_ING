# Simulador de Capacidad de Ingeniería

Migración del dashboard de Power BI de planificación de capacidad a una aplicación web con
simulación de recursos en vivo.

| Carpeta | Contenido |
|---|---|
| [`docs/PROPUESTA_TECNICA.md`](docs/PROPUESTA_TECNICA.md) | Propuesta técnica completa: arquitectura, modelo de datos, SharePoint, reemplazo de las tablas DAX, simulación, escenarios, viabilidad y diagramas. |
| [`prototipo/`](prototipo) | Prototipo funcional en HTML/JS: Gantt de proyectos arrastrable (inicio y duración), matriz de ocupación con semáforo, gráfico demanda vs capacidad, edición de recursos y de los parámetros del modelo (tablas de HH y curvas), escenarios, comparación, exportación CSV/JSON y reporte PDF. Abrir `prototipo/index.html`. |
| [`backend/`](backend) | Motor de cálculo en Python (`app/motor.py`), API FastAPI, repositorio SQLite/SQL Server y conector SharePoint vía Microsoft Graph. |
| [`db/schema.sql`](db/schema.sql) | Modelo de datos. |
| [`data/proyectos.csv`](data/proyectos.csv) | Lista de proyectos exportada de SharePoint (DIM_Proyecto). Es la fuente de los proyectos. |
| [`data/sample_data.json`](data/sample_data.json) | Dataset que usa la herramienta: proyectos del CSV + parámetros, curvas y capacidad **ilustrativos**. |

## Uso rápido

```bash
# Prototipo: abrir prototipo/index.html en el navegador (funciona sin servidor).

# Tests del motor, paridad Python/JavaScript y API
cd backend && python -m unittest discover -s tests -t .

# API + prototipo en http://localhost:8000  (docs en /docs)
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

## Actualizar la lista de proyectos

- **Desde la herramienta:** botón **Importar** → elegir el CSV exportado de la lista SharePoint. Reemplaza los proyectos (parámetros, curvas y recursos no cambian) y muestra avisos de datos raros. Ctrl+Z deshace.
- **Para todos los usuarios:** reemplazar `data/proyectos.csv` y correr `cd backend && python -m app.datos_ejemplo` (regenera `data/sample_data.json` y `prototipo/data.js`). Para revisar el mapeo antes: `python -m app.importar_csv ../data/proyectos.csv`.

Mapeo: "N/A" = sin dato · fecha dd/mm/aaaa → mes · **Calendario Fijo = Si → no simulable** · el **Tamaño** se deriva de la potencia con las tablas de HH Parque si el CSV no lo trae.
