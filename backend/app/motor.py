"""Motor de cálculo de capacidad de Ingeniería.

Reemplaza las tablas calculadas y medidas DAX de Power BI:

    DIM_Proyecto ──► componentes()        ≙ Forecast_Componentes
    componentes × DIM_Curvas ──► forecast() ≙ Forecast_Mes_V4
    forecast vs capacidad ──► calcular()    ≙ medidas Ocupación, Máxima Ocupación,
                                              Primer Mes Crítico, HH Excedidas, Pareto

Es una implementación pura (sin dependencias) y determinista. ``prototipo/engine.js``
es su espejo en JavaScript; ``tests/test_motor.py`` verifica que ambos coinciden.

Los meses se representan como "YYYY-MM" en la interfaz y como un índice entero
(año*12 + mes-1) internamente.
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict

TIPOS_CLIENTE = ["DPI", "DNN", "O&M"]
MAX_MESES = 120  # tope del horizonte extendido automáticamente (10 años)
MESES_SENSIBILIDAD = 3  # una sensibilidad DNN arranca 3 meses después de que termina el bloque anterior


# ---------------------------------------------------------------- utilidades
def mes_idx(ym: str) -> int:
    y, m = (int(x) for x in ym.split("-"))
    return y * 12 + (m - 1)


def mes_str(i: int) -> str:
    return f"{i // 12}-{i % 12 + 1:02d}"


def interpolar(puntos: list[list[float]], x: float) -> float:
    """Interpolación lineal por tramos; fuera de rango extrapola con el tramo extremo."""
    p = sorted(puntos, key=lambda q: q[0])
    if len(p) == 1:
        return float(p[0][1])
    i = 0
    while i < len(p) - 2 and x > p[i + 1][0]:
        i += 1
    (x0, y0), (x1, y1) = p[i], p[i + 1]
    return max(0.0, y0 + (y1 - y0) * (x - x0) / (x1 - x0))


def _vacio(v) -> bool:
    return v is None or v == ""


# ------------------------------------------------------- HH por componente
TAMANOS = ["Chico", "Mediano", "Grande", "Muy Grande"]


def tamano(p: dict, params: dict) -> str:
    """Tamaño del proyecto: el cargado, o el que corresponde a su potencia.

    Sin dato, se toma el mayor tamaño cuya tabla de HH Parque empieza en una
    potencia menor o igual a la del proyecto (Solar: 300 MW -> Muy Grande).
    """
    if not _vacio(p.get("tamano")):
        return p["tamano"]
    mw = float(p.get("potencia") or 0)
    elegido = TAMANOS[0]
    for t in TAMANOS:
        puntos = params["parque"].get(f"{p.get('tecnologia')}|{t}")
        if puntos and min(pt[0] for pt in puntos) <= mw:
            elegido = t
    return elegido


def hh_parque_base(p: dict, params: dict) -> float:
    puntos = params["parque"].get(f"{p['tecnologia']}|{tamano(p, params)}")
    if not puntos:
        return 0.0
    return interpolar(puntos, float(p.get("potencia") or 0))


# ---------------------------------------------------------------- tecnología «Otro»
HH_PERSONA_DEFECTO = 140 * 0.85


def es_otro(p: dict) -> bool:
    return p.get("tecnologia") == "Otro"


def plan_hh(p: dict, params: dict) -> dict:
    """Plan de recursos manual de un proyecto «Otro» en HH: {especialidad: [HH mes 1..n]}.

    planManual = {"unidad": "personas" | "hh", "meses": n, "valores": {especialidad: [..]}}
    En personas equivalentes se convierte con params["hhPersonaMes"] (HH/persona × eficiencia).
    """
    plan = p.get("planManual") or {}
    n = int(plan.get("meses") or 0)
    f = float(params.get("hhPersonaMes") or HH_PERSONA_DEFECTO) if plan.get("unidad", "personas") == "personas" else 1.0
    out = {}
    for esp, vals in (plan.get("valores") or {}).items():
        v = [float(x or 0) * f for x in (vals or [])][:n]
        out[esp] = v + [0.0] * (n - len(v))
    return out


def curvas_de(p: dict, curvas: dict, params: dict) -> dict:
    """Curvas a usar para un proyecto: las de DIM_Curvas o, si es «Otro», la de su plan manual."""
    if not es_otro(p):
        return curvas
    hh = plan_hh(p, params)
    total = sum(sum(v) for v in hh.values())
    return {"Manual": {e: [x / total for x in v] for e, v in hh.items()} if total > 0 else {}}


def componentes(p: dict, params: dict) -> list[dict]:
    """Descompone un proyecto en componentes con HH y curva (Forecast_Componentes)."""
    if es_otro(p):
        total = sum(sum(v) for v in plan_hh(p, params).values())
        return [{"componente": "Otro", "curva": "Manual", "hh": total}]
    tipo = p["tipoCliente"]
    if tipo == "DNN":
        hh = p["hhProy"] if not _vacio(p.get("hhProy")) else (
            hh_parque_base(p, params) * params["factorDNN"].get(p.get("nivelDNN"), 0))
        return [{"componente": "DNN", "curva": p.get("nivelDNN"), "hh": float(hh)}]
    if tipo == "O&M":
        hh = p["hhProy"] if not _vacio(p.get("hhProy")) else hh_parque_base(p, params) * params["factorOM"]
        return [{"componente": "O&M", "curva": "O&M", "hh": float(hh)}]

    comps = []
    hh = p["hhParque"] if not _vacio(p.get("hhParque")) else hh_parque_base(p, params)
    comps.append({"componente": "Parque", "curva": p["tecnologia"], "hh": float(hh)})
    if not _vacio(p.get("est")):
        if not _vacio(p.get("hhEt")):
            hh = p["hhEt"]
        else:
            hh = params["et"].get(tamano(p, params), 0)
            if p["est"] == "Ampliación ET":
                hh *= params["factorAmpliacionET"]
        comps.append({"componente": "ET", "curva": p["est"], "hh": float(hh)})
    if not _vacio(p.get("linea")):
        if not _vacio(p.get("hhLinea")):
            hh = p["hhLinea"]
        else:
            hh = params["linea"].get(tamano(p, params), 0)
            if p["linea"] == "Línea MT":
                hh *= params["factorLineaMT"]
        comps.append({"componente": "Línea", "curva": p["linea"], "hh": float(hh)})
    return comps


# ------------------------------------------------------------- escenarios
def aplicar_escenario(datos: dict, escenario: dict | None) -> tuple[list[dict], dict]:
    """Devuelve (proyectos, capacidad) con los cambios del escenario aplicados.

    escenario = {
      "proyectos": {"<id>": {"incluir": bool, "desplazamiento": int, "potencia": float,
                              "factorSolapamiento": float, "fechaInicio": "YYYY-MM",
                              "duracion": int}},          # meses; None = la de las curvas
      "capacidad": {"dotacion": {...}, "hhMesPersona": n, "eficiencia": f,
                    "subcontratoHH": {...}, "eventos": [...],   # eventos se suman a los base
                    "staff": [...]}   # reemplaza la nómina; con nómina, "dotacion" no se usa
    }
    """
    escenario = escenario or {}
    cambios = escenario.get("proyectos", {})
    proyectos = []
    for p in datos["proyectos"]:
        q = dict(p)
        q.setdefault("incluir", True)
        q["desplazamiento"] = 0
        c = cambios.get(str(p["id"]))
        if c:
            q.update({k: v for k, v in c.items() if k != "id"})
        proyectos.append(q)

    cap = copy.deepcopy(datos["capacidad"])
    cc = escenario.get("capacidad", {})
    for k in ("hhMesPersona", "eficiencia"):
        if k in cc:
            cap[k] = cc[k]
    cap["dotacion"].update(cc.get("dotacion", {}))
    cap.setdefault("subcontratoHH", {}).update(cc.get("subcontratoHH", {}))
    if "staff" in cc:
        cap["staff"] = copy.deepcopy(cc["staff"])
    cap["eventos"] = list(cap.get("eventos", [])) + list(cc.get("eventos", []))
    return proyectos, cap


# --------------------------------------------------------------- forecast
def largo_curva(curvas: dict, nombre: str) -> int:
    """Meses de una curva (la especialidad más larga)."""
    return max((len(v) for v in (curvas.get(nombre) or {}).values()), default=0)


def duracion_base(p: dict, curvas: dict, params: dict) -> int:
    """Duración del proyecto según sus curvas: la del componente más largo."""
    curvas = curvas_de(p, curvas, params)
    return max((largo_curva(curvas, c["curva"]) for c in componentes(p, params)), default=0)


def reescalar(factores: list[float], n_nuevo: int) -> list[float]:
    """Estira o comprime una curva a ``n_nuevo`` meses conservando su suma y su forma.

    Trata la curva como una densidad constante dentro de cada mes y reparte la
    acumulada original sobre la nueva grilla de meses.
    """
    n = len(factores)
    if n_nuevo == n or n == 0:
        return list(factores)
    acum = [0.0]
    for f in factores:
        acum.append(acum[-1] + f)

    def c(t: float) -> float:
        i = math.floor(t)
        if i >= n:
            return acum[n]
        return acum[i] + factores[i] * (t - i)

    return [c((j + 1) * n / n_nuevo) - c(j * n / n_nuevo) for j in range(n_nuevo)]


def largo_componente(n_c: int, n_base: int, duracion) -> int:
    """Meses de un componente cuando el proyecto dura ``duracion`` (proporcional al componente más largo)."""
    if _vacio(duracion) or not n_base:
        return n_c
    return max(1, math.floor(n_c * int(duracion) / n_base + 0.5))


def sensibilidades(p: dict) -> int:
    """Bloques adicionales de un DNN (0 para DPI y O&M)."""
    if p.get("tipoCliente") != "DNN":
        return 0
    return max(0, int(p.get("sensibilidades") or 0))


def bloques(p: dict, curvas: dict, params: dict) -> list[tuple[int, int]]:
    """[(desplazamiento, duración)] del bloque original y de cada sensibilidad.

    Cada sensibilidad repite el trabajo (mismas HH, curva y duración) y arranca
    MESES_SENSIBILIDAD meses después del último mes del bloque anterior.
    """
    curvas = curvas_de(p, curvas, params)
    comps = componentes(p, params)
    n_base = max((largo_curva(curvas, c["curva"]) for c in comps), default=0)
    dur = max((largo_componente(largo_curva(curvas, c["curva"]), n_base, p.get("duracion")) for c in comps), default=0)
    paso = dur - 1 + MESES_SENSIBILIDAD
    return [(b * paso, dur) for b in range(sensibilidades(p) + 1)]


def forecast(proyectos: list[dict], curvas: dict, params: dict) -> list[dict]:
    """Distribución mensual de HH por proyecto/componente/especialidad (Forecast_Mes_V4).

    HH Forecast = HHComponente × Factor × Factor Solapamiento

    Si el proyecto tiene ``duracion`` (meses), cada curva se reescala en el tiempo
    con ``reescalar``: las HH totales no cambian, cambia su intensidad mensual.
    """
    filas = []
    for p in proyectos:
        if not p.get("incluir", True):
            continue
        inicio = mes_idx(p["fechaInicio"]) + int(p.get("desplazamiento") or 0)
        solap = p.get("factorSolapamiento")
        solap = 1.0 if _vacio(solap) or es_otro(p) else float(solap)  # «Otro»: sin solapamiento
        cv = curvas_de(p, curvas, params)
        comps = componentes(p, params)
        n_base = max((largo_curva(cv, c["curva"]) for c in comps), default=0)
        desplazamientos = [d for d, _ in bloques(p, curvas, params)]
        for c in comps:
            curva = cv.get(c["curva"]) or {}
            n_c = largo_curva(cv, c["curva"])
            n_nuevo = largo_componente(n_c, n_base, p.get("duracion"))
            for esp, factores in curva.items():
                if n_nuevo != n_c:
                    factores = reescalar(factores + [0.0] * (n_c - len(factores)), n_nuevo)
                for b, off in enumerate(desplazamientos):  # b = 0 original, 1.. sensibilidades
                    for k, f in enumerate(factores):
                        if f == 0:
                            continue
                        filas.append({
                            "proyectoId": p["id"], "proyecto": p["proyecto"],
                            "tipoCliente": p["tipoCliente"], "componente": c["componente"], "bloque": b,
                            "curva": c["curva"], "mes": inicio + off + k, "mesCurva": k + 1, "especialidad": esp,
                            "factor": f, "hhComponente": c["hh"],
                            "hh": c["hh"] * f * solap,
                        })
    return filas


def persona_activa(s: dict, mes: int) -> bool:
    if not _vacio(s.get("desde")) and mes < mes_idx(s["desde"]):
        return False
    if not _vacio(s.get("hasta")) and mes > mes_idx(s["hasta"]):
        return False
    return True


def personas_base(cap: dict, mes: int, esp: str) -> float:
    """Personas de una especialidad en un mes.

    Con nómina (capacidad.staff = [{nombre, especialidad, dedicacion, desde, hasta}])
    se cuentan las personas activas ese mes, ponderadas por su dedicación (0,5 = media
    jornada). Las personas con simulado = False figuran en la lista pero no suman.
    Sin nómina se usa la dotación numérica (capacidad.dotacion).
    """
    staff = cap.get("staff") or []
    if staff:
        total = 0.0
        for s in staff:
            if s.get("simulado") is False:  # destildado en la nómina: sus horas no cuentan
                continue
            if s.get("especialidad") == esp and persona_activa(s, mes):
                total += 1.0 if _vacio(s.get("dedicacion")) else float(s["dedicacion"])
        return total
    return cap["dotacion"].get(esp, 0)


def capacidad_mes(cap: dict, mes: int, esp: str) -> float:
    personas = personas_base(cap, mes, esp)
    for ev in cap.get("eventos", []):
        if ev["especialidad"] != esp:
            continue
        if mes < mes_idx(ev["desde"]):
            continue
        if ev.get("hasta") and mes > mes_idx(ev["hasta"]):
            continue
        personas += ev["delta"]
    personas = max(0, personas)
    return personas * cap["hhMesPersona"] * cap["eficiencia"] + cap.get("subcontratoHH", {}).get(esp, 0)


def _ocupacion(d: float, c: float) -> float:
    if c > 0:
        return d / c
    return math.inf if d > 0 else 0.0


# ---------------------------------------------------------------- cálculo
def calcular(datos: dict, escenario: dict | None = None) -> dict:
    proyectos, cap = aplicar_escenario(datos, escenario)
    esps = datos["especialidades"]
    params = {**datos["parametros"], "hhPersonaMes": cap["hhMesPersona"] * cap["eficiencia"]}
    filas = forecast(proyectos, datos["curvas"], params)

    m0 = mes_idx(datos["horizonte"]["desde"])
    n = datos["horizonte"]["meses"]
    # Si algún proyecto termina después del horizonte configurado, se extiende hasta
    # su último mes (salvo horizonte.extender = False) para no perder demanda.
    if datos["horizonte"].get("extender", True) and filas:
        n = max(n, min(max(f["mes"] for f in filas) - m0 + 1, MAX_MESES))
    meses = list(range(m0, m0 + n))
    # Los indicadores miran hacia adelante: desde kpiDesde (p. ej. el mes actual).
    # Los meses anteriores se muestran en la matriz pero no cuentan como exceso.
    kpi0 = mes_idx(datos["horizonte"]["kpiDesde"]) if datos["horizonte"].get("kpiDesde") else m0
    meses_kpi = [m for m in meses if m >= kpi0]

    dem = {m: {e: 0.0 for e in esps} for m in meses}
    dem_tipo = {m: {t: 0.0 for t in TIPOS_CLIENTE} for m in meses}
    por_proy = defaultdict(float)
    por_tipo = defaultdict(float)
    por_comp = defaultdict(float)
    for f in filas:
        por_proy[f["proyecto"]] += f["hh"]
        por_tipo[f["tipoCliente"]] += f["hh"]
        por_comp[f["componente"]] += f["hh"]
        if f["mes"] in dem:
            dem[f["mes"]][f["especialidad"]] += f["hh"]
            dem_tipo[f["mes"]][f["tipoCliente"]] += f["hh"]

    capm = {m: {e: capacidad_mes(cap, m, e) for e in esps} for m in meses}
    ocup = {m: {e: _ocupacion(dem[m][e], capm[m][e]) for e in esps} for m in meses}

    max_ocup = {"valor": 0.0, "mes": None, "especialidad": None}
    primer_critico = None
    hh_exc = 0.0
    cuellos = {}
    for e in esps:
        cuellos[e] = {"mesesCriticos": 0, "hhExcedidas": 0.0, "maxOcupacion": 0.0,
                      "mesPico": None, "maxExceso": 0.0, "primerMesCritico": None}
    for m in meses_kpi:
        criticas = []
        for e in esps:
            o, exc = ocup[m][e], max(0.0, dem[m][e] - capm[m][e])
            hh_exc += exc
            cu = cuellos[e]
            cu["hhExcedidas"] += exc
            cu["maxExceso"] = max(cu["maxExceso"], exc)
            if o > cu["maxOcupacion"]:
                cu["maxOcupacion"], cu["mesPico"] = o, mes_str(m)
            if o > 1:
                cu["mesesCriticos"] += 1
                criticas.append(e)
                if cu["primerMesCritico"] is None:
                    cu["primerMesCritico"] = mes_str(m)
            if o > max_ocup["valor"]:
                max_ocup = {"valor": o, "mes": mes_str(m), "especialidad": e}
        if criticas and primer_critico is None:
            primer_critico = {"mes": mes_str(m), "especialidades": criticas}

    hh_persona = cap["hhMesPersona"] * cap["eficiencia"]
    for cu in cuellos.values():
        cu["personasAdicionales"] = math.ceil(round(cu["maxExceso"] / hh_persona, 6)) if hh_persona else None

    total = sum(por_proy.values())
    acum = 0.0
    pareto = []
    for nombre, hh in sorted(por_proy.items(), key=lambda kv: (-kv[1], kv[0])):
        acum += hh
        pareto.append({"proyecto": nombre, "hh": hh,
                       "pct": hh / total if total else 0, "pctAcum": acum / total if total else 0})

    return {
        "meses": [mes_str(m) for m in meses],
        "kpiDesde": mes_str(max(kpi0, m0)),
        "especialidades": esps,
        "demanda": [[dem[m][e] for e in esps] for m in meses],
        "capacidad": [[capm[m][e] for e in esps] for m in meses],
        "ocupacion": [[ocup[m][e] for e in esps] for m in meses],
        "demandaPorTipo": [[dem_tipo[m][t] for t in TIPOS_CLIENTE] for m in meses],
        "kpis": {
            "maxOcupacion": max_ocup,
            "primerMesCritico": primer_critico,
            "hhExcedidas": hh_exc,
            "hhForecastHorizonte": sum(sum(dem[m].values()) for m in meses_kpi),
            "hhForecastTotal": total,
        },
        "cuellos": cuellos,
        "pareto": pareto,
        "mixTipoCliente": {t: por_tipo.get(t, 0.0) for t in TIPOS_CLIENTE},
        "mixComponente": dict(por_comp),
    }


def detalle(datos: dict, escenario: dict | None, mes: str, especialidad: str) -> list[dict]:
    """Qué proyectos/componentes explican la demanda de una celda de la matriz."""
    proyectos, cap = aplicar_escenario(datos, escenario)
    m = mes_idx(mes)
    agg = defaultdict(float)
    params = {**datos["parametros"], "hhPersonaMes": cap["hhMesPersona"] * cap["eficiencia"]}
    for f in forecast(proyectos, datos["curvas"], params):
        if f["mes"] == m and f["especialidad"] == especialidad:
            comp = f["componente"] + (f" · sensibilidad {f['bloque']}" if f.get("bloque") else "")
            agg[(f["proyecto"], comp)] += f["hh"]
    return [{"proyecto": p, "componente": c, "hh": hh}
            for (p, c), hh in sorted(agg.items(), key=lambda kv: -kv[1])]


def mejor_inicio(datos: dict, escenario: dict | None, proyecto_id, desde: int = -3, hasta: int = 12) -> dict:
    """Prueba desplazamientos de inicio y devuelve el que minimiza las HH excedidas."""
    escenario = copy.deepcopy(escenario or {})
    escenario.setdefault("proyectos", {})
    clave = str(proyecto_id)
    base = escenario["proyectos"].get(clave, {})
    pruebas = []
    for d in range(desde, hasta + 1):
        escenario["proyectos"][clave] = {**base, "desplazamiento": d}
        k = calcular(datos, escenario)["kpis"]
        pruebas.append({"desplazamiento": d, "hhExcedidas": k["hhExcedidas"],
                        "maxOcupacion": k["maxOcupacion"]["valor"]})
    mejor = min(pruebas, key=lambda r: (round(r["hhExcedidas"], 6), abs(r["desplazamiento"])))
    return {"mejor": mejor, "pruebas": pruebas}
