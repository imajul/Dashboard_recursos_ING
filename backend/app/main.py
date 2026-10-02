"""API REST del Simulador de Capacidad de Ingeniería (FastAPI).

    uvicorn app.main:app --reload          (desde backend/)

La simulación interactiva corre en el navegador (engine.js) para responder en
milisegundos; la API es la fuente de verdad: guarda escenarios, recalcula con el
motor Python (mismo algoritmo, verificado por tests de paridad), materializa
Forecast_Mes_V4 y sincroniza SharePoint.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import motor, repositorio
from .datos_ejemplo import dataset

DB = os.environ.get("CAPACIDAD_DB", str(repositorio.RAIZ / "data" / "capacidad.db"))

app = FastAPI(title="Capacidad de Ingeniería", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


def get_cn():
    nueva = not Path(DB).exists()
    cn = repositorio.conectar(DB)
    if nueva:  # primera ejecución: esquema + datos de ejemplo
        repositorio.crear_esquema(cn)
        repositorio.cargar_dataset(cn, dataset())
    try:
        yield cn
    finally:
        cn.close()


def usuario_actual() -> str:
    # En producción: validar el JWT de Entra ID (MSAL en el front) y devolver el UPN.
    return "dev@local"


def _json_seguro(o):
    """inf (capacidad 0 con demanda) no es JSON válido: se envía como null."""
    if isinstance(o, float):
        return None if math.isinf(o) or math.isnan(o) else o
    if isinstance(o, dict):
        return {k: _json_seguro(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_json_seguro(v) for v in o]
    return o


class Escenario(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    cambios: dict = Field(default_factory=dict, description="Forma de motor.aplicar_escenario")


class Simulacion(BaseModel):
    cambios: dict = Field(default_factory=dict)


# ---------------------------------------------------------------- lectura
@app.get("/api/datos")
def datos(cn=Depends(get_cn)):
    """Dataset completo (proyectos, curvas, parámetros, capacidad) para el front."""
    return repositorio.leer_dataset(cn)


@app.get("/api/proyectos")
def proyectos(cn=Depends(get_cn)):
    d = repositorio.leer_dataset(cn)
    return [p | {"componentes": motor.componentes(p, d["parametros"])} for p in d["proyectos"]]


# ---------------------------------------------------------------- simulación
@app.post("/api/simular")
def simular(body: Simulacion, cn=Depends(get_cn)):
    """Calcula KPIs, matriz y pareto para un conjunto de cambios sin guardarlo."""
    return _json_seguro(motor.calcular(repositorio.leer_dataset(cn), body.cambios))


@app.get("/api/detalle")
def detalle(mes: str, especialidad: str, escenario_id: int | None = None, cn=Depends(get_cn)):
    cambios = _cambios(cn, escenario_id)
    return motor.detalle(repositorio.leer_dataset(cn), cambios, mes, especialidad)


@app.get("/api/proyectos/{proyecto_id}/mejor-inicio")
def mejor_inicio(proyecto_id: int, escenario_id: int | None = None, desde: int = -3, hasta: int = 12,
                 cn=Depends(get_cn)):
    d = repositorio.leer_dataset(cn)
    if not any(p["id"] == proyecto_id for p in d["proyectos"]):
        raise HTTPException(404, "Proyecto inexistente")
    return _json_seguro(motor.mejor_inicio(d, _cambios(cn, escenario_id), proyecto_id, desde, hasta))


# ---------------------------------------------------------------- escenarios
@app.get("/api/escenarios")
def escenarios(cn=Depends(get_cn)):
    return repositorio.listar_escenarios(cn)


@app.post("/api/escenarios", status_code=201)
def crear_escenario(body: Escenario, cn=Depends(get_cn), user=Depends(usuario_actual)):
    esc_id = repositorio.guardar_escenario(cn, body.nombre, body.cambios, user, body.descripcion)
    _recalcular(cn, esc_id)
    return repositorio.obtener_escenario(cn, esc_id)


@app.put("/api/escenarios/{esc_id}")
def modificar_escenario(esc_id: int, body: Escenario, cn=Depends(get_cn), user=Depends(usuario_actual)):
    if repositorio.obtener_escenario(cn, esc_id) is None:
        raise HTTPException(404, "Escenario inexistente")
    repositorio.guardar_escenario(cn, body.nombre, body.cambios, user, body.descripcion, esc_id)
    _recalcular(cn, esc_id)
    return repositorio.obtener_escenario(cn, esc_id)


@app.get("/api/escenarios/{esc_id}/resultado")
def resultado(esc_id: int, cn=Depends(get_cn)):
    return _json_seguro(motor.calcular(repositorio.leer_dataset(cn), _cambios(cn, esc_id)))


@app.get("/api/comparar")
def comparar(ids: str, cn=Depends(get_cn)):
    """ids=0,3,5 (0 = base). Devuelve los KPIs de cada escenario lado a lado."""
    d = repositorio.leer_dataset(cn)
    out = []
    for i in (int(x) for x in ids.split(",") if x.strip()):
        r = motor.calcular(d, _cambios(cn, i or None))
        out.append({"escenarioId": i, "kpis": r["kpis"], "cuellos": r["cuellos"]})
    return _json_seguro(out)


# ---------------------------------------------------------------- SharePoint
@app.post("/api/sync/sharepoint")
def sync(cn=Depends(get_cn)):
    from .sharepoint import sincronizar

    try:
        resumen = sincronizar(cn)
    except KeyError as e:
        raise HTTPException(500, f"Falta la variable de entorno {e}") from e
    _recalcular(cn, None)
    return resumen


def _cambios(cn, esc_id: int | None) -> dict:
    if esc_id is None:
        return {}
    esc = repositorio.obtener_escenario(cn, esc_id)
    if esc is None:
        raise HTTPException(404, "Escenario inexistente")
    return esc["cambios"]


def _recalcular(cn, esc_id: int | None) -> None:
    d = repositorio.leer_dataset(cn)
    cambios = _cambios(cn, esc_id)
    proyectos, _ = motor.aplicar_escenario(d, cambios)
    filas = motor.forecast(proyectos, d["curvas"], d["parametros"])
    kpis = motor.calcular(d, cambios)["kpis"] if esc_id is not None else None
    repositorio.materializar_forecast(cn, esc_id, filas, kpis)


# El prototipo se sirve desde la misma API (http://localhost:8000/)
_proto = repositorio.RAIZ / "prototipo"
if _proto.exists():
    app.mount("/", StaticFiles(directory=_proto, html=True), name="prototipo")
