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

ESPECIALIDADES = ["Civiles", "Coordinadores", "Eléctricos", "Electrónicos", "Mecánicos"]

# Duración (meses) y reparto de HH por especialidad de cada curva.
CURVAS_DEF = {
    #               meses  Civ   Coord Elec  Electr Mec
    "Solar":         (12, [0.25, 0.15, 0.40, 0.10, 0.10]),
    "Bess":          (9,  [0.15, 0.15, 0.40, 0.20, 0.10]),
    "Eólico":        (15, [0.30, 0.15, 0.30, 0.05, 0.20]),
    "Termico":       (15, [0.20, 0.15, 0.25, 0.10, 0.30]),
    "ET Nueva":      (10, [0.20, 0.10, 0.55, 0.10, 0.05]),
    "Ampliación ET": (6,  [0.15, 0.10, 0.60, 0.10, 0.05]),
    "Línea MT":      (6,  [0.35, 0.10, 0.50, 0.00, 0.05]),
    "Línea AT":      (9,  [0.40, 0.10, 0.45, 0.00, 0.05]),
    "DNN Cat1":      (3,  [0.15, 0.30, 0.35, 0.05, 0.15]),
    "DNN Cat2":      (9,  [0.20, 0.25, 0.35, 0.05, 0.15]),
    "O&M":           (12, [0.10, 0.20, 0.40, 0.15, 0.15]),
}
# Momento del pico de cada especialidad dentro de la curva (fracción de la duración).
CENTRO_ESP = [0.30, 0.50, 0.60, 0.72, 0.55]


def _forma(n: int, centro: float, plana: bool) -> list[float]:
    if plana:
        return [1.0] * n
    # Campana suave: pico en `centro`, colas que no llegan a cero.
    return [0.15 + math.exp(-((((i + 0.5) / n) - centro) ** 2) / 0.06) for i in range(n)]


def generar_curvas() -> dict:
    """Devuelve {curva: {especialidad: [factor_mes_1, ..., factor_mes_n]}}.

    La suma de todos los factores de una curva es ~1 (redondeo a 4 decimales),
    igual que en DIM_Curvas.
    """
    curvas: dict = {}
    for nombre, (n, reparto) in CURVAS_DEF.items():
        plana = nombre == "O&M"
        curvas[nombre] = {}
        for esp, peso, centro in zip(ESPECIALIDADES, reparto, CENTRO_ESP):
            forma = _forma(n, centro, plana)
            total = sum(forma)
            curvas[nombre][esp] = [round(peso * f / total, 4) for f in forma]
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
    "dotacion": {"Civiles": 8, "Coordinadores": 6, "Eléctricos": 14, "Electrónicos": 4, "Mecánicos": 5},
    "subcontratoHH": {},
    # Altas/bajas ya conocidas (delta de personas desde/hasta un mes).
    "eventos": [
        {"especialidad": "Eléctricos", "desde": "2027-03", "hasta": None, "delta": -1,
         "nota": "Jubilación prevista"},
    ],
}

P = None  # alias corto para campos vacíos


def _p(id_, nombre, tipo, tec, mw, tam, desde, est=P, linea=P, nivel=P, solap=1.0,
       simulable=False, estado="Confirmado", hh_proy=P):
    return {
        "id": id_, "proyecto": nombre, "tipoCliente": tipo, "tecnologia": tec,
        "potencia": mw, "tamano": tam, "nivelDNN": nivel, "estado": estado,
        "fechaInicio": desde, "est": est, "linea": linea, "simulable": simulable,
        "hhParque": P, "hhEt": P, "hhLinea": P, "hhProy": hh_proy,
        "factorSolapamiento": solap,
    }


PROYECTOS = [
    _p(1, "PPSDV", "DPI", "Solar", 300, "Muy Grande", "2026-09", "ET Nueva", "Línea AT", simulable=True),
    _p(2, "PE Pampa Sur", "DPI", "Eólico", 180, "Grande", "2026-11", "ET Nueva", "Línea AT", simulable=True),
    _p(3, "BESS Norte I", "DPI", "Bess", 120, "Grande", "2026-10", "Ampliación ET", "Línea MT", solap=0.6),
    _p(4, "BESS Norte II", "DPI", "Bess", 80, "Mediano", "2027-01", "Ampliación ET", solap=0.6, simulable=True),
    _p(5, "BESS Cuyo", "DPI", "Bess", 60, "Mediano", "2027-03", linea="Línea MT", solap=0.6, simulable=True),
    _p(6, "PS Valle Fértil", "DPI", "Solar", 90, "Mediano", "2027-02", "ET Nueva", "Línea MT", simulable=True),
    _p(7, "CC Luján", "DPI", "Termico", 250, "Grande", "2027-05", "Ampliación ET", estado="Probable", simulable=True),
    _p(8, "PS Altiplano", "DPI", "Solar", 450, "Muy Grande", "2027-06", "ET Nueva", "Línea AT",
       estado="Probable", simulable=True),
    _p(9, "DNN Eólico Patagonia", "DNN", "Eólico", 400, "Muy Grande", "2026-10", nivel="DNN Cat2", estado="En estudio"),
    _p(10, "DNN Solar Catamarca", "DNN", "Solar", 200, "Grande", "2026-12", nivel="DNN Cat1", estado="En estudio"),
    _p(11, "DNN BESS Litoral", "DNN", "Bess", 150, "Grande", "2027-02", nivel="DNN Cat1", estado="En estudio"),
    _p(12, "DNN Solar La Rioja", "DNN", "Solar", 350, "Muy Grande", "2027-04", nivel="DNN Cat2", estado="En estudio"),
    _p(13, "O&M Parques Solares", "O&M", "Solar", 600, "Muy Grande", "2027-01", hh_proy=2400),
    _p(14, "O&M Parques Eólicos", "O&M", "Eólico", 350, "Muy Grande", "2027-01", hh_proy=1800),
    _p(15, "O&M BESS", "O&M", "Bess", 200, "Grande", "2026-10", hh_proy=1200),
]


def dataset() -> dict:
    return {
        "meta": {"origen": "ejemplo", "nota": "Datos ilustrativos, no reales"},
        "horizonte": {"desde": "2026-10", "meses": 24},
        "especialidades": ESPECIALIDADES,
        "parametros": PARAMETROS,
        "capacidad": CAPACIDAD,
        "curvas": generar_curvas(),
        "proyectos": PROYECTOS,
    }


def main() -> None:
    raiz = Path(__file__).resolve().parents[2]
    datos = dataset()
    texto = json.dumps(datos, ensure_ascii=False, indent=1)
    (raiz / "data" / "sample_data.json").write_text(texto + "\n", encoding="utf-8")
    (raiz / "prototipo" / "data.js").write_text(
        "// Generado por backend/app/datos_ejemplo.py — datos ilustrativos.\n"
        f"window.SAMPLE_DATA = {texto};\n",
        encoding="utf-8",
    )
    print("Escrito data/sample_data.json y prototipo/data.js")


if __name__ == "__main__":
    main()
