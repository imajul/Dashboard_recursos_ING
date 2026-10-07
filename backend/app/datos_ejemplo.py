"""Genera el dataset de ejemplo (proyectos, curvas, parámetros y capacidad).

Los valores son ilustrativos: replican la estructura de las listas SharePoint
(DIM_Proyecto, DIM_Curvas, Capacidad) para que el motor y el prototipo puedan
ejecutarse sin conexión. En producción estos datos llegan por la sincronización
con SharePoint (ver ``sharepoint.py``).

Uso:
    python -m app.datos_ejemplo          # escribe data/sample_data.json y prototipo/data.js
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ESPECIALIDADES = ["Civiles", "Coordinadores", "Eléctricos", "Electrónicos", "Mecánicos", "Estudios"]

# Duración (meses) y reparto de HH por especialidad de cada curva.
CURVAS_DEF = {
    # Estudios arranca en 0: su porción de cada curva se define en Parámetros → Curvas.
    #               meses  Civ   Coord Elec  Electr Mec   Estud
    "Solar":         (12, [0.25, 0.15, 0.40, 0.10, 0.10, 0.00]),
    "Bess":          (9,  [0.15, 0.15, 0.40, 0.20, 0.10, 0.00]),
    "Eólico":        (15, [0.30, 0.15, 0.30, 0.05, 0.20, 0.00]),
    "Termico":       (15, [0.20, 0.15, 0.25, 0.10, 0.30, 0.00]),
    "ET Nueva":      (10, [0.20, 0.10, 0.55, 0.10, 0.05, 0.00]),
    "Ampliación ET": (6,  [0.15, 0.10, 0.60, 0.10, 0.05, 0.00]),
    "Línea MT":      (6,  [0.35, 0.10, 0.50, 0.00, 0.05, 0.00]),
    "Línea AT":      (9,  [0.40, 0.10, 0.45, 0.00, 0.05, 0.00]),
    "DNN Cat1":      (3,  [0.15, 0.30, 0.35, 0.05, 0.15, 0.00]),
    "DNN Cat2":      (9,  [0.20, 0.25, 0.35, 0.05, 0.15, 0.00]),
    "O&M":           (12, [0.10, 0.20, 0.40, 0.15, 0.15, 0.00]),
}
# Momento del pico de cada especialidad dentro de la curva (fracción de la duración).
CENTRO_ESP = [0.30, 0.50, 0.60, 0.72, 0.55, 0.20]


def _forma(n: int, centro: float, plana: bool) -> list[float]:
    if plana:
        return [1.0] * n
    # Campana suave: pico en `centro`, colas que no llegan a cero.
    return [0.15 + math.exp(-((((i + 0.5) / n) - centro) ** 2) / 0.06) for i in range(n)]


def enteros_a_100(curva: dict) -> dict:
    """Redondea una curva a porcentajes enteros que suman exactamente 100 (método del mayor resto)."""
    celdas = [(e, k, f) for e, fs in curva.items() for k, f in enumerate(fs)]
    total = sum(f for _, _, f in celdas)
    exactos = [(e, k, f / total * 100) for e, k, f in celdas]
    enteros = {(e, k): int(x) for e, k, x in exactos}
    faltan = 100 - sum(enteros.values())
    for e, k, x in sorted(exactos, key=lambda c: -(c[2] - int(c[2])))[:faltan]:
        enteros[(e, k)] += 1
    return {e: [enteros[(e, k)] / 100 for k in range(len(fs))] for e, fs in curva.items()}


def generar_curvas() -> dict:
    """Devuelve {curva: {especialidad: [factor_mes_1, ..., factor_mes_n]}}.

    Cada factor es un porcentaje entero (0,07 = 7 %) y la suma de la curva es
    exactamente 1.
    """
    curvas: dict = {}
    for nombre, (n, reparto) in CURVAS_DEF.items():
        plana = nombre == "O&M"
        curvas[nombre] = {}
        for esp, peso, centro in zip(ESPECIALIDADES, reparto, CENTRO_ESP):
            forma = _forma(n, centro, plana)
            total = sum(forma)
            curvas[nombre][esp] = [peso * f / total for f in forma]
        curvas[nombre] = enteros_a_100(curvas[nombre])  # se cargan como % enteros
    return curvas


PARAMETROS = {
    # HH Parque: interpolación lineal por (Tecnología, Tamaño) entre puntos [MW, HH].
    "parque": {
        "Solar|Chico": [[1, 800], [20, 1500]],
        "Solar|Mediano": [[20, 1500], [100, 3500]],
        "Solar|Grande": [[100, 3500], [300, 7000]],
        "Solar|Muy Grande": [[300, 7000], [500, 10000]],
        "Bess|Chico": [[1, 600], [20, 1200]],
        "Bess|Mediano": [[20, 1200], [100, 3000]],
        "Bess|Grande": [[100, 3000], [250, 5500]],
        "Bess|Muy Grande": [[250, 5500], [500, 8500]],
        "Eólico|Chico": [[1, 1000], [30, 2000]],
        "Eólico|Mediano": [[30, 2000], [100, 4500]],
        "Eólico|Grande": [[100, 4500], [300, 8500]],
        "Eólico|Muy Grande": [[300, 8500], [600, 13000]],
        "Termico|Chico": [[1, 1200], [50, 2500]],
        "Termico|Mediano": [[50, 2500], [150, 5000]],
        "Termico|Grande": [[150, 5000], [400, 9000]],
        "Termico|Muy Grande": [[400, 9000], [800, 14000]],
    },
    "et": {"Chico": 500, "Mediano": 1000, "Grande": 2000, "Muy Grande": 3000},
    "factorAmpliacionET": 0.30,
    "linea": {"Chico": 300, "Mediano": 600, "Grande": 1200, "Muy Grande": 1800},
    "factorLineaMT": 0.70,
    # DNN y O&M: fracción de las HH de parque equivalentes (si no hay HH Estimadas Proy).
    "factorDNN": {"DNN Cat1": 0.06, "DNN Cat2": 0.15},
    "factorOM": 0.08,
}

CAPACIDAD = {
    "hhMesPersona": 140,
    "eficiencia": 0.85,
    "dotacion": {"Civiles": 8, "Coordinadores": 6, "Eléctricos": 14, "Electrónicos": 4, "Mecánicos": 5, "Estudios": 2},
    "subcontratoHH": {},
    # Las altas y bajas se cargan en la nómina (ingreso / egreso de cada persona); el motor
    # sigue aceptando "eventos" por compatibilidad con planes viejos y la API.
    "eventos": [],
}

# Proyectos reales: export de la lista SharePoint DIM_Proyecto (data/proyectos.csv).
CSV_PROYECTOS = Path(__file__).resolve().parents[2] / "data" / "proyectos.csv"


def proyectos() -> list[dict]:
    from .importar_csv import leer_archivo

    return leer_archivo(CSV_PROYECTOS)[0]


def dataset() -> dict:
    return {
        "meta": {"origen": "data/proyectos.csv", "version": "proyectos-csv-2026-10-h2026-01",
                 "nota": "Proyectos del CSV de SharePoint; parámetros, curvas y capacidad ilustrativos"},
        "horizonte": {"desde": "2026-01", "meses": 33},  # kpiDesde: None = mes actual
        "especialidades": ESPECIALIDADES,
        "parametros": PARAMETROS,
        "capacidad": CAPACIDAD,
        "curvas": generar_curvas(),
        "proyectos": proyectos(),
    }


def main() -> None:
    raiz = Path(__file__).resolve().parents[2]
    datos = dataset()
    texto = json.dumps(datos, ensure_ascii=False, indent=1)
    (raiz / "data" / "sample_data.json").write_text(texto + "\n", encoding="utf-8")
    (raiz / "prototipo" / "data.js").write_text(
        "// Generado por backend/app/datos_ejemplo.py — proyectos de data/proyectos.csv.\n"
        f"window.SAMPLE_DATA = {texto};\n",
        encoding="utf-8",
    )
    print("Escrito data/sample_data.json y prototipo/data.js")


if __name__ == "__main__":
    main()
