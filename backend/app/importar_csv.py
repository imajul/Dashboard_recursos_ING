"""Importa la lista de proyectos desde el CSV exportado de SharePoint (DIM_Proyecto).

Columnas esperadas (el orden no importa; se ignoran las que no se usan):

    Proyectos · Nombre · Tipo Cliente · Nivel DNN · Tecnología · Factor Solapa · Potencia ·
    Tensión POE · Est Transformadora · Linea · Fecha Inicio · Estado · Calendario Fijo · % Avance
    (opcionales, los agrega «Exportar → Lista de proyectos»: Duración meses · Tamaño · Incluir · Plan Manual)

Reglas de mapeo:
- "N/A" o vacío -> sin dato.
- Números con coma decimal ("0,43").
- Fecha "dd/mm/aaaa hh:mm" -> mes "aaaa-mm" (el modelo trabaja por mes).
- "Et Nueva" -> "ET Nueva"; "Cat 2" -> "DNN Cat2" (solo para DNN).
- Calendario Fijo = "Si" -> proyecto NO simulable (no se mueve ni se estira).
- Tecnología "Otro": sus HH salen de la columna Plan Manual (JSON con unidad, meses y valores por especialidad).
- El CSV no trae Tamaño: lo deriva el motor a partir de la potencia (motor.tamano).

Uso:
    python -m app.importar_csv ../data/proyectos.csv      # muestra el resultado y los avisos
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

NA = {"", "n/a", "na", "-", "none"}


def _txt(v) -> str | None:
    v = (v or "").strip()
    return None if v.lower() in NA else v


def _num(v) -> float | None:
    v = _txt(v)
    if v is None:
        return None
    return float(v.replace(".", "").replace(",", ".") if v.count(",") == 1 and v.count(".") >= 1 else v.replace(",", "."))


def _mes(v) -> str | None:
    v = _txt(v)
    if v is None:
        return None
    fecha = v.split()[0]
    if "/" in fecha:
        d, m, a = fecha.split("/")
        return f"{int(a):04d}-{int(m):02d}"
    return fecha[:7]  # ya viene ISO


def _tecnologia(v):
    v = _txt(v)
    return {"bess": "Bess", "solar": "Solar", "eólico": "Eólico", "eolico": "Eólico",
            "termico": "Termico", "térmico": "Termico", "otro": "Otro", "otra": "Otro"}.get((v or "").lower(), v)


def _est(v):
    v = _txt(v)
    if v is None:
        return None
    k = v.lower()
    if "nueva" in k:
        return "ET Nueva"
    if "ampl" in k:
        return "Ampliación ET"
    return v


def _linea(v):
    v = _txt(v)
    if v is None:
        return None
    k = v.upper()
    if "AT" in k.split() or k.endswith(" AT"):
        return "Línea AT"
    if "MT" in k.split() or k.endswith(" MT"):
        return "Línea MT"
    return v


def _nivel(v, tipo):
    v = _txt(v)
    if tipo != "DNN" or v is None:
        return None
    n = "".join(ch for ch in v if ch.isdigit())
    return f"DNN Cat{n}" if n else v


def leer(texto: str) -> tuple[list[dict], list[str]]:
    """Devuelve (proyectos, avisos)."""
    filas = list(csv.DictReader(io.StringIO(texto.lstrip("﻿"))))
    proyectos, avisos = [], []
    for i, f in enumerate(filas, start=1):
        f = {(k or "").strip(): v for k, v in f.items()}
        codigo = _txt(f.get("Proyectos") or f.get("Proyecto"))
        if not codigo:
            continue
        tipo = _txt(f.get("Tipo Cliente"))
        p = {
            "id": i,
            "proyecto": codigo,
            "nombre": _txt(f.get("Nombre")),
            "tipoCliente": tipo,
            "tecnologia": _tecnologia(f.get("Tecnología") or f.get("Tecnologia")),
            "potencia": _num(f.get("Potencia")),
            "tamano": _txt(f.get("Tamaño")),
            "nivelDNN": _nivel(f.get("Nivel DNN"), tipo),
            "estado": _txt(f.get("Estado")),
            "fechaInicio": _mes(f.get("Fecha Inicio")),
            "est": _est(f.get("Est Transformadora")),
            "linea": _linea(f.get("Linea") or f.get("Línea")),
            "simulable": (_txt(f.get("Calendario Fijo")) or "No").lower() not in ("si", "sí", "yes", "true", "1"),
            # HH manuales: si vienen cargadas pisan el modelo para ese proyecto
            "hhParque": _num(f.get("HH Estimadas Parque")), "hhEt": _num(f.get("HH Estimadas ET")),
            "hhLinea": _num(f.get("HH Estimadas Línea") or f.get("HH Estimadas Linea")),
            "hhProy": _num(f.get("HH Estimadas Proy")), "notaHH": _txt(f.get("Motivo HH")),
            "factorSolapamiento": _num(f.get("Factor Solapa") or f.get("Factor Solapamiento")) or 1.0,
            "duracion": int(_num(f.get("Duración meses")) or 0) or None,
            "sensibilidades": int(_num(f.get("Sensibilidades")) or 0) or None,
            "tensionPOE": _num(f.get("Tensión POE")),
            "avance": _num(f.get("% Avance")),
        }
        if (_txt(f.get("Incluir")) or "").lower() in ("no", "false", "0"):
            p["incluir"] = False
        plan = _txt(f.get("Plan Manual"))  # tecnología «Otro»: plan de recursos en JSON
        if plan:
            try:
                p["planManual"] = json.loads(plan)
            except ValueError:
                avisos.append(f"{codigo}: «Plan Manual» ilegible (se ignora)")
        if p["tecnologia"] == "Otro" and not (p.get("planManual") or {}).get("meses"):
            avisos.append(f"{codigo}: tecnología Otro sin plan de recursos")
        if tipo not in ("DPI", "DNN", "O&M"):
            avisos.append(f"{codigo}: Tipo Cliente desconocido {tipo!r}")
        if not p["fechaInicio"]:
            avisos.append(f"{codigo}: sin Fecha Inicio")
        if tipo == "DNN" and p["nivelDNN"] not in ("DNN Cat1", "DNN Cat2"):
            avisos.append(f"{codigo}: DNN sin Nivel DNN válido")
        if tipo == "O&M" and _txt(f.get("Nivel DNN")):
            avisos.append(f"{codigo}: es O&M y tiene Nivel DNN {f.get('Nivel DNN')!r} (se ignora)")
        if tipo != "DPI" and (p["est"] or p["linea"]):
            avisos.append(f"{codigo}: ET/Línea cargadas en un proyecto {tipo} (no se usan)")
        proyectos.append(p)
    return proyectos, avisos


def leer_archivo(ruta: str | Path) -> tuple[list[dict], list[str]]:
    return leer(Path(ruta).read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    from .datos_ejemplo import PARAMETROS
    from .motor import componentes, tamano

    ps, avisos = leer_archivo(sys.argv[1])
    for p in ps:
        hh = sum(c["hh"] for c in componentes(p, PARAMETROS))
        print(f"{p['proyecto']:6} {p['tipoCliente']:4} {p['tecnologia']:8} {p['potencia']:>6} MW  "
              f"{tamano(p, PARAMETROS):10} inicio {p['fechaInicio']}  solap {p['factorSolapamiento']:.2f}  "
              f"{'fijo' if not p['simulable'] else '    '}  {hh:8.0f} HH")
    for a in avisos:
        print("AVISO:", a)
