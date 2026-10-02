"""Acceso a datos (SQLite en desarrollo; misma interfaz sobre SQL Server en producción).

Convierte entre las tablas de ``db/schema.sql`` y el diccionario ``datos`` que
consume ``motor.calcular``.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCHEMA = RAIZ / "db" / "schema.sql"


def conectar(ruta: str | Path) -> sqlite3.Connection:
    cn = sqlite3.connect(ruta)
    cn.row_factory = sqlite3.Row
    cn.execute("PRAGMA foreign_keys = ON")
    return cn


def crear_esquema(cn: sqlite3.Connection) -> None:
    cn.executescript(SCHEMA.read_text(encoding="utf-8"))


def cargar_dataset(cn: sqlite3.Connection, datos: dict) -> None:
    """Carga un dataset (p. ej. datos_ejemplo.dataset()) en las tablas."""
    with cn:
        for i, e in enumerate(datos["especialidades"]):
            cn.execute("INSERT OR REPLACE INTO especialidad VALUES (?,?)", (e, i))
        cn.execute("DELETE FROM dim_curva")
        for curva, esps in datos["curvas"].items():
            for esp, factores in esps.items():
                cn.executemany("INSERT INTO dim_curva VALUES (?,?,?,?)",
                               [(curva, k + 1, esp, f) for k, f in enumerate(factores)])
        p = datos["parametros"]
        cn.execute("DELETE FROM param_parque")
        for clave, puntos in p["parque"].items():
            tec, tam = clave.split("|")
            cn.executemany("INSERT INTO param_parque VALUES (?,?,?,?)", [(tec, tam, mw, hh) for mw, hh in puntos])
        cn.execute("DELETE FROM param_valor")
        filas = [("et", k, v) for k, v in p["et"].items()] + [("linea", k, v) for k, v in p["linea"].items()]
        filas += [("factorDNN", k, v) for k, v in p["factorDNN"].items()]
        filas += [("factor", k, p[k]) for k in ("factorAmpliacionET", "factorLineaMT", "factorOM")]
        cn.executemany("INSERT INTO param_valor VALUES (?,?,?)", filas)
        cap = datos["capacidad"]
        cn.execute("INSERT OR REPLACE INTO capacidad_global VALUES (1,?,?,?,?)",
                   (cap["hhMesPersona"], cap["eficiencia"], datos["horizonte"]["desde"], datos["horizonte"]["meses"]))
        for e in datos["especialidades"]:
            cn.execute("INSERT OR REPLACE INTO capacidad_especialidad VALUES (?,?,?)",
                       (e, cap["dotacion"].get(e, 0), cap.get("subcontratoHH", {}).get(e, 0)))
        cn.execute("DELETE FROM capacidad_evento WHERE escenario_id IS NULL")
        cn.executemany(
            "INSERT INTO capacidad_evento (escenario_id, especialidad, desde, hasta, delta, nota) VALUES (NULL,?,?,?,?,?)",
            [(ev["especialidad"], ev["desde"], ev.get("hasta"), ev["delta"], ev.get("nota")) for ev in cap.get("eventos", [])])
        for pr in datos["proyectos"]:
            upsert_proyecto(cn, pr)


def upsert_proyecto(cn: sqlite3.Connection, p: dict, sp_item_id: str | None = None, sp_modified: str | None = None) -> None:
    cn.execute(
        """INSERT INTO dim_proyecto (id, sp_item_id, proyecto, tipo_cliente, tecnologia, potencia_mw, tamano, nivel_dnn,
               estado, fecha_inicio, est_transformadora, linea, simulable, hh_parque_manual, hh_et_manual,
               hh_linea_manual, hh_proy_manual, factor_solapamiento, duracion_meses, sp_modified)
           VALUES (:id,:sp,:proyecto,:tipoCliente,:tecnologia,:potencia,:tamano,:nivelDNN,:estado,:fechaInicio,:est,
                   :linea,:simulable,:hhParque,:hhEt,:hhLinea,:hhProy,:factorSolapamiento,:duracion,:spm)
           ON CONFLICT(id) DO UPDATE SET
               proyecto=excluded.proyecto, tipo_cliente=excluded.tipo_cliente, tecnologia=excluded.tecnologia,
               potencia_mw=excluded.potencia_mw, tamano=excluded.tamano, nivel_dnn=excluded.nivel_dnn,
               estado=excluded.estado, fecha_inicio=excluded.fecha_inicio,
               est_transformadora=excluded.est_transformadora, linea=excluded.linea, simulable=excluded.simulable,
               hh_parque_manual=excluded.hh_parque_manual, hh_et_manual=excluded.hh_et_manual,
               hh_linea_manual=excluded.hh_linea_manual, hh_proy_manual=excluded.hh_proy_manual,
               factor_solapamiento=excluded.factor_solapamiento, duracion_meses=excluded.duracion_meses,
               sp_modified=excluded.sp_modified,
               sincronizado_ts=datetime('now')""",
        {**p, "sp": sp_item_id or p.get("spItemId"), "spm": sp_modified,
         "simulable": 1 if p.get("simulable") else 0, "duracion": p.get("duracion"),
         "factorSolapamiento": 1.0 if p.get("factorSolapamiento") in (None, "") else p["factorSolapamiento"]},
    )


def leer_dataset(cn: sqlite3.Connection) -> dict:
    """Reconstruye el diccionario ``datos`` del motor desde la base."""
    esps = [r["nombre"] for r in cn.execute("SELECT nombre FROM especialidad ORDER BY orden")]
    curvas: dict = defaultdict(lambda: defaultdict(list))
    for r in cn.execute("SELECT * FROM dim_curva ORDER BY tipo_curva, especialidad, mes"):
        lista = curvas[r["tipo_curva"]][r["especialidad"]]
        while len(lista) < r["mes"] - 1:
            lista.append(0.0)
        lista.append(r["factor"])
    parque: dict = defaultdict(list)
    for r in cn.execute("SELECT * FROM param_parque ORDER BY tecnologia, tamano, mw"):
        parque[f"{r['tecnologia']}|{r['tamano']}"].append([r["mw"], r["hh"]])
    pv: dict = defaultdict(dict)
    for r in cn.execute("SELECT * FROM param_valor"):
        pv[r["grupo"]][r["clave"]] = r["valor"]
    g = cn.execute("SELECT * FROM capacidad_global WHERE id = 1").fetchone()
    cap_esp = {r["especialidad"]: r for r in cn.execute("SELECT * FROM capacidad_especialidad")}
    eventos = [dict(especialidad=r["especialidad"], desde=r["desde"], hasta=r["hasta"], delta=r["delta"], nota=r["nota"])
               for r in cn.execute("SELECT * FROM capacidad_evento WHERE escenario_id IS NULL ORDER BY id")]
    proyectos = [{
        "id": r["id"], "proyecto": r["proyecto"], "tipoCliente": r["tipo_cliente"], "tecnologia": r["tecnologia"],
        "potencia": r["potencia_mw"], "tamano": r["tamano"], "nivelDNN": r["nivel_dnn"], "estado": r["estado"],
        "fechaInicio": r["fecha_inicio"], "est": r["est_transformadora"], "linea": r["linea"],
        "simulable": bool(r["simulable"]), "hhParque": r["hh_parque_manual"], "hhEt": r["hh_et_manual"],
        "hhLinea": r["hh_linea_manual"], "hhProy": r["hh_proy_manual"], "factorSolapamiento": r["factor_solapamiento"],
        "duracion": r["duracion_meses"],
    } for r in cn.execute("SELECT * FROM dim_proyecto ORDER BY id")]
    return {
        "horizonte": {"desde": g["horizonte_desde"], "meses": g["horizonte_meses"]},
        "especialidades": esps,
        "parametros": {
            "parque": dict(parque), "et": pv["et"], "linea": pv["linea"], "factorDNN": pv["factorDNN"],
            "factorAmpliacionET": pv["factor"]["factorAmpliacionET"], "factorLineaMT": pv["factor"]["factorLineaMT"],
            "factorOM": pv["factor"]["factorOM"],
        },
        "capacidad": {
            "hhMesPersona": g["hh_mes_persona"], "eficiencia": g["eficiencia"],
            "dotacion": {e: cap_esp[e]["personas"] for e in cap_esp},
            "subcontratoHH": {e: cap_esp[e]["subcontrato_hh"] for e in cap_esp if cap_esp[e]["subcontrato_hh"]},
            "eventos": eventos,
        },
        "curvas": {k: dict(v) for k, v in curvas.items()},
        "proyectos": proyectos,
    }


# ---------------------------------------------------------------- escenarios
def listar_escenarios(cn: sqlite3.Connection) -> list[dict]:
    return [dict(r) | {"cambios": json.loads(r["cambios_json"])}
            for r in cn.execute("SELECT * FROM escenario WHERE estado <> 'archivado' ORDER BY modificado_ts DESC")]


def obtener_escenario(cn: sqlite3.Connection, esc_id: int) -> dict | None:
    r = cn.execute("SELECT * FROM escenario WHERE id = ?", (esc_id,)).fetchone()
    return None if r is None else dict(r) | {"cambios": json.loads(r["cambios_json"])}


def guardar_escenario(cn: sqlite3.Connection, nombre: str, cambios: dict, usuario: str | None,
                      descripcion: str | None = None, esc_id: int | None = None) -> int:
    with cn:
        if esc_id is None:
            cur = cn.execute("INSERT INTO escenario (nombre, descripcion, cambios_json, creado_por) VALUES (?,?,?,?)",
                             (nombre, descripcion, json.dumps(cambios, ensure_ascii=False), usuario))
            esc_id = cur.lastrowid
            accion = "crear"
        else:
            cn.execute("UPDATE escenario SET nombre=?, descripcion=?, cambios_json=?, modificado_ts=datetime('now') WHERE id=?",
                       (nombre, descripcion, json.dumps(cambios, ensure_ascii=False), esc_id))
            accion = "modificar"
        cn.execute("INSERT INTO auditoria (usuario, entidad, entidad_id, accion, detalle) VALUES (?,?,?,?,?)",
                   (usuario, "escenario", str(esc_id), accion, json.dumps(cambios, ensure_ascii=False)))
    return esc_id


def materializar_forecast(cn: sqlite3.Connection, esc_id: int | None, filas: list[dict], kpis: dict | None) -> None:
    """Persiste Forecast_Mes_V4 y los KPIs del escenario (auditoría / consumo externo)."""
    from .motor import mes_str  # import local para evitar ciclo

    with cn:
        cn.execute("DELETE FROM forecast_mes WHERE escenario_id IS ?", (esc_id,))
        cn.executemany(
            "INSERT INTO forecast_mes VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(esc_id, f["proyectoId"], f["componente"], f["curva"], f.get("mesCurva", 0), f["especialidad"],
              f["factor"], f["hhComponente"], f["hh"], mes_str(f["mes"]) + "-01") for f in filas])
        if esc_id is not None and kpis is not None:
            cn.execute("INSERT OR REPLACE INTO resultado_escenario (escenario_id, kpis_json) VALUES (?,?)",
                       (esc_id, json.dumps(kpis, ensure_ascii=False, default=str)))
