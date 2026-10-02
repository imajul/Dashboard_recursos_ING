-- Modelo de datos del Simulador de Capacidad de Ingeniería.
-- Dialecto: SQLite (desarrollo). Para SQL Server: INTEGER PRIMARY KEY -> INT IDENTITY,
-- TEXT -> NVARCHAR(n), REAL -> DECIMAL(12,4), datetime('now') -> SYSUTCDATETIME().
--
-- Capas:
--   1. Maestros replicados desde SharePoint (dim_proyecto, dim_curva)
--   2. Parámetros del modelo (param_*), editables por el administrador
--   3. Capacidad y escenarios (capacidad_*, escenario*)
--   4. Resultados materializados (forecast_mes, resultado_escenario) para auditoría y consumo externo

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- 1. maestros
CREATE TABLE IF NOT EXISTS dim_proyecto (
    id                   INTEGER PRIMARY KEY,
    sp_item_id           TEXT UNIQUE,              -- id del ítem en la lista SharePoint
    proyecto             TEXT NOT NULL,
    tipo_cliente         TEXT NOT NULL CHECK (tipo_cliente IN ('DPI','DNN','O&M')),
    tecnologia           TEXT NOT NULL,            -- Solar | Bess | Eólico | Termico
    potencia_mw          REAL,
    tamano               TEXT CHECK (tamano IN ('Chico','Mediano','Grande','Muy Grande')),
    nivel_dnn            TEXT CHECK (nivel_dnn IN ('DNN Cat1','DNN Cat2') OR nivel_dnn IS NULL),
    estado               TEXT,
    fecha_inicio         TEXT NOT NULL,            -- 'YYYY-MM'
    est_transformadora   TEXT CHECK (est_transformadora IN ('ET Nueva','Ampliación ET') OR est_transformadora IS NULL),
    linea                TEXT CHECK (linea IN ('Línea MT','Línea AT') OR linea IS NULL),
    simulable            INTEGER NOT NULL DEFAULT 0,
    hh_parque_manual     REAL,                     -- NULL = calcular con el modelo
    hh_et_manual         REAL,
    hh_linea_manual      REAL,
    hh_proy_manual       REAL,
    factor_solapamiento  REAL NOT NULL DEFAULT 1 CHECK (factor_solapamiento BETWEEN 0 AND 1),
    sp_modified          TEXT,                     -- lastModifiedDateTime de Graph
    sincronizado_ts      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS especialidad (
    nombre  TEXT PRIMARY KEY,
    orden   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_curva (
    tipo_curva    TEXT NOT NULL,                   -- Solar, ET Nueva, Línea AT, DNN Cat1, O&M, ...
    mes           INTEGER NOT NULL CHECK (mes >= 1),
    especialidad  TEXT NOT NULL REFERENCES especialidad(nombre),
    factor        REAL NOT NULL CHECK (factor >= 0),
    PRIMARY KEY (tipo_curva, mes, especialidad)
);

-- ---------------------------------------------------------------- 2. parámetros
-- Puntos de interpolación de HH Parque: (tecnología, tamaño, MW) -> HH
CREATE TABLE IF NOT EXISTS param_parque (
    tecnologia  TEXT NOT NULL,
    tamano      TEXT NOT NULL,
    mw          REAL NOT NULL,
    hh          REAL NOT NULL,
    PRIMARY KEY (tecnologia, tamano, mw)
);

-- HH por tamaño para ET y Línea, y factores escalares (factorAmpliacionET, factorLineaMT, factorOM, ...)
CREATE TABLE IF NOT EXISTS param_valor (
    grupo  TEXT NOT NULL,                          -- 'et' | 'linea' | 'factor' | 'factorDNN'
    clave  TEXT NOT NULL,                          -- 'Grande' | 'factorAmpliacionET' | 'DNN Cat1'
    valor  REAL NOT NULL,
    PRIMARY KEY (grupo, clave)
);

-- ---------------------------------------------------------------- 3. capacidad y escenarios
CREATE TABLE IF NOT EXISTS capacidad_global (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    hh_mes_persona  REAL NOT NULL DEFAULT 140,
    eficiencia      REAL NOT NULL DEFAULT 0.85,
    horizonte_desde TEXT NOT NULL,                 -- 'YYYY-MM'
    horizonte_meses INTEGER NOT NULL DEFAULT 24
);

CREATE TABLE IF NOT EXISTS capacidad_especialidad (
    especialidad    TEXT PRIMARY KEY REFERENCES especialidad(nombre),
    personas        INTEGER NOT NULL DEFAULT 0,
    subcontrato_hh  REAL NOT NULL DEFAULT 0
);

-- Altas / bajas conocidas (escenario_id NULL = forman parte de la base)
CREATE TABLE IF NOT EXISTS capacidad_evento (
    id            INTEGER PRIMARY KEY,
    escenario_id  INTEGER REFERENCES escenario(id) ON DELETE CASCADE,
    especialidad  TEXT NOT NULL REFERENCES especialidad(nombre),
    desde         TEXT NOT NULL,
    hasta         TEXT,
    delta         INTEGER NOT NULL,
    nota          TEXT
);

-- Un escenario guarda SOLO los cambios respecto de la base (JSON con la forma que
-- consume motor.aplicar_escenario). Así la base puede re-sincronizarse desde
-- SharePoint sin invalidar los escenarios.
CREATE TABLE IF NOT EXISTS escenario (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT NOT NULL,
    descripcion   TEXT,
    cambios_json  TEXT NOT NULL DEFAULT '{}',
    estado        TEXT NOT NULL DEFAULT 'borrador' CHECK (estado IN ('borrador','publicado','archivado')),
    creado_por    TEXT,
    creado_ts     TEXT NOT NULL DEFAULT (datetime('now')),
    modificado_ts TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------- 4. resultados
-- Equivalente materializado de Forecast_Mes_V4 (por escenario; NULL = base)
CREATE TABLE IF NOT EXISTS forecast_mes (
    escenario_id   INTEGER REFERENCES escenario(id) ON DELETE CASCADE,
    proyecto_id    INTEGER NOT NULL REFERENCES dim_proyecto(id),
    componente     TEXT NOT NULL,                  -- Parque | ET | Línea | DNN | O&M
    tipo_curva     TEXT NOT NULL,
    mes_curva      INTEGER NOT NULL,
    especialidad   TEXT NOT NULL,
    factor         REAL NOT NULL,
    hh_componente  REAL NOT NULL,
    hh_forecast    REAL NOT NULL,
    fecha_forecast TEXT NOT NULL                   -- 'YYYY-MM-01'
);
CREATE INDEX IF NOT EXISTS ix_forecast_mes ON forecast_mes (escenario_id, fecha_forecast, especialidad);

CREATE TABLE IF NOT EXISTS resultado_escenario (
    escenario_id  INTEGER PRIMARY KEY REFERENCES escenario(id) ON DELETE CASCADE,
    calculado_ts  TEXT NOT NULL DEFAULT (datetime('now')),
    kpis_json     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY,
    origen      TEXT NOT NULL,                     -- 'DIM_Proyecto' | 'DIM_Curvas'
    inicio_ts   TEXT NOT NULL,
    fin_ts      TEXT,
    leidos      INTEGER,
    actualizados INTEGER,
    error       TEXT,
    delta_link  TEXT                               -- @odata.deltaLink para la próxima sincronización incremental
);

CREATE TABLE IF NOT EXISTS auditoria (
    id        INTEGER PRIMARY KEY,
    ts        TEXT NOT NULL DEFAULT (datetime('now')),
    usuario   TEXT,
    entidad   TEXT NOT NULL,
    entidad_id TEXT,
    accion    TEXT NOT NULL,
    detalle   TEXT
);

-- Vista de ocupación para herramientas externas (Excel / Power BI en modo lectura)
CREATE VIEW IF NOT EXISTS v_demanda_mes AS
SELECT escenario_id, fecha_forecast, especialidad, SUM(hh_forecast) AS hh_forecast
FROM forecast_mes
GROUP BY escenario_id, fecha_forecast, especialidad;
