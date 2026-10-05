# Simulador de Capacidad de Ingeniería

Migración del dashboard de Power BI de planificación de capacidad a una aplicación web con
simulación de recursos en vivo.

| Carpeta | Contenido |
|---|---|
| [`docs/PROPUESTA_TECNICA.md`](docs/PROPUESTA_TECNICA.md) | Propuesta técnica completa: arquitectura, modelo de datos, SharePoint, reemplazo de las tablas DAX, simulación, escenarios, viabilidad y diagramas. |
| [`prototipo/`](prototipo) | Prototipo funcional en HTML/JS: Gantt de proyectos arrastrable (inicio y duración), matriz de ocupación con semáforo, gráfico demanda vs capacidad, edición de recursos y de los parámetros del modelo (tablas de HH y curvas), escenarios, comparación, exportación CSV/JSON y reporte PDF. Abrir `prototipo/index.html`. |
| [`dist/`](dist) | **Versión para usar en equipo**: `capacidad-ingenieria.html` (la herramienta en un solo archivo) y `LEEME.txt` (guía). Se copian a una carpeta sincronizada con SharePoint. |
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

## Uso colaborativo en una carpeta sincronizada (OneDrive / SharePoint)

La herramienta trabaja sobre una carpeta de Windows sincronizada con SharePoint. No necesita servidor
ni cuentas de Claude o GitHub: alcanza con la cuenta de Microsoft de la empresa y Edge o Chrome.

```
📁 Capacidad Ingeniería  (sincronizada con SharePoint)
 ├─ capacidad-ingenieria.html   la herramienta (doble clic) — dist/capacidad-ingenieria.html
 ├─ LEEME.txt                   guía para los usuarios       — dist/LEEME.txt
 ├─ plan-capacidad.json         plan vigente (lo crea y actualiza la herramienta)
 ├─ escenarios\                 simulaciones del equipo, un archivo por escenario
 └─ historial\                  copia de cada versión guardada (últimas 60)
```

- **Guardar** (Ctrl+S) escribe `plan-capacidad.json` con revisión, autor y fecha, y deja una copia en `historial`.
- Cada 20 segundos (y al volver a la ventana) la herramienta revisa la carpeta: si otro guardó y vos no
  tenés cambios pendientes, carga la versión nueva sola; si tenés cambios, avisa y ofrece guardarlos como
  escenario, cargar la versión del otro o reemplazarla. Nunca pisa en silencio.
- Detecta las «copias en conflicto» que crea OneDrive (`plan-capacidad-NOMBREPC.json`) y permite abrirlas y borrarlas.
- Usa la API de acceso a archivos del navegador (Edge/Chrome); la carpeta elegida se recuerda y, al
  reabrir, el navegador puede pedir confirmar el permiso con un clic.
- La línea de tiempo arranca en ene-26 (Recursos → Horizonte) y se extiende sola si un proyecto se mueve o
  estira más allá del final (hasta 10 años). Los indicadores cuentan desde el mes actual
  (Recursos → «Indicadores desde»); los meses anteriores se ven sombreados.
- **La herramienta es la base de datos oficial de proyectos.** Botón «Proyectos»: tabla editable con todos
  los campos de DIM_Proyecto (más duración, tamaño, incluir) y validaciones. Importar CSV reemplaza la lista
  (con vista previa de altas, cambios y bajas); Exportar → Lista de proyectos genera el CSV en el mismo formato.
- **Staff de Ingeniería (Recursos):** nómina con nombre, especialidad, dedicación, ingreso y egreso; la
  cantidad de personas por especialidad y mes sale de la lista (`capacidad.staff`; sin lista se usa
  `capacidad.dotacion`). Pegar desde Excel, vacantes desde «Nivelar», cambios en el registro.
- **HH manuales por proyecto:** en el panel del proyecto, HH por componente (modelo vs. asignadas) con motivo;
  vacío = modelo. Se exportan en las columnas «HH Estimadas …».
- **Tecnología «Otro»:** proyectos fuera de las tecnologías predefinidas llevan su propio plan de recursos
  (`planManual`: especialidad × mes, en personas equivalentes o HH) en lugar de tablas de HH y curvas; sin
  factor de solapamiento. Editor con generador desde un total de HH, escalado desde la tabla, reescalado al
  cambiar la duración y exportación del plan. El motor (Python y JS) lo trata como una curva «Manual».
- **Registro de cambios:** cada guardado anota qué cambió (altas, bajas, campos con valor anterior y nuevo,
  recursos, parámetros) y quién; se ve en el historial y en el aviso de conflicto.
- Sin carpeta conectada sigue funcionando como antes (datos en el navegador, Exportar/Importar JSON).

Para generar o actualizar los archivos de la carpeta: `python scripts/build_standalone.py`
(antes, si cambió la lista de proyectos: `cd backend && python -m app.datos_ejemplo`).

## Compartir la herramienta sin cuenta

`dist/capacidad-ingenieria.html` es la herramienta completa en un único archivo (motor + datos adentro).
Se adjunta por mail o Teams, o se deja en una carpeta compartida o biblioteca de SharePoint; quien lo
recibe lo **descarga y lo abre con doble clic** en Chrome o Edge. Funciona sin internet, salvo el
botón Reporte PDF.

- Cada persona trabaja sobre su copia: lo que cambia queda en su navegador. Para pasar un escenario,
  **Exportar → Escenario (JSON)** y el otro lo abre con **Importar**.
- Después de actualizar proyectos o parámetros, regenerar el archivo:
  `cd backend && python -m app.datos_ejemplo && cd .. && python scripts/build_standalone.py`.
