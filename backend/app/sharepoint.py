"""Sincronización con SharePoint Online vía Microsoft Graph.

Flujo (app-only, sin usuario interactivo):
    1. MSAL obtiene un token con client credentials (App Registration en Entra ID
       con permiso de aplicación Sites.Selected, concedido solo al sitio de Ingeniería).
    2. GET /sites/{site-id}/lists/{lista}/items?expand=fields  (paginado con @odata.nextLink)
       o, a partir de la segunda corrida, /items/delta con el @odata.deltaLink guardado.
    3. Cada ítem se mapea a la forma del motor y se hace UPSERT en dim_proyecto / dim_curva.

Variables de entorno:
    SP_TENANT_ID, SP_CLIENT_ID, SP_CLIENT_SECRET (o certificado),
    SP_SITE_ID   (p. ej. "contoso.sharepoint.com,<guid-sitio>,<guid-web>"),
    SP_LIST_PROYECTOS="DIM_Proyecto", SP_LIST_CURVAS="DIM_Curvas"

Los nombres internos de columna de SharePoint suelen diferir del título visible
(p. ej. "HH Estimadas Parque" -> "HH_x0020_Estimadas_x0020_Parque"). Ajustar
``MAPEO_PROYECTO`` a los nombres internos reales (se ven en
/lists/{lista}/columns).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterator

GRAPH = "https://graph.microsoft.com/v1.0"

# nombre interno SharePoint -> clave del motor
MAPEO_PROYECTO = {
    "Title": "proyecto",
    "Tipo_x0020_Cliente": "tipoCliente",
    "Tecnolog_x00ed_a": "tecnologia",
    "Potencia": "potencia",
    "Tama_x00f1_o": "tamano",
    "Nivel_x0020_DNN": "nivelDNN",
    "Estado": "estado",
    "Fecha_x0020_Inicio": "fechaInicio",
    "Est_x0020_Transformadora": "est",
    "L_x00ed_nea": "linea",
    "Proyecto_x0020_Simulable": "simulable",
    "HH_x0020_Estimadas_x0020_Parque": "hhParque",
    "HH_x0020_Estimadas_x0020_ET": "hhEt",
    "HH_x0020_Estimadas_x0020_L_x00ed_nea": "hhLinea",
    "HH_x0020_Estimadas_x0020_Proy": "hhProy",
    "Factor_x0020_Solapamiento": "factorSolapamiento",
    "Duraci_x00f3_n_x0020_meses": "duracion",  # opcional: vacío = la de las curvas
}
MAPEO_CURVA = {"Tecnolog_x00ed_a": "tipoCurva", "Mes": "mes", "Especialidad": "especialidad", "Factor": "factor"}

# Normalización de valores de elección que llegan con variantes
NORMALIZA = {
    "tipoCliente": {"Dirección de Proyectos": "DPI", "OyM": "O&M", "O & M": "O&M"},
    "tecnologia": {"BESS": "Bess", "Térmico": "Termico", "Eolico": "Eólico"},
    "nivelDNN": {"Cat1": "DNN Cat1", "Cat2": "DNN Cat2", "1": "DNN Cat1", "2": "DNN Cat2"},
    "est": {"Nueva": "ET Nueva", "Ampliación": "Ampliación ET", "No": None, "": None},
    "linea": {"MT": "Línea MT", "AT": "Línea AT", "No": None, "": None},
}


class GraphClient:
    def __init__(self, tenant: str, client_id: str, secret: str):
        import httpx  # dependencias opcionales: solo se necesitan para sincronizar
        import msal

        self._app = msal.ConfidentialClientApplication(
            client_id, authority=f"https://login.microsoftonline.com/{tenant}", client_credential=secret)
        self._http = httpx.Client(timeout=30)

    @classmethod
    def desde_entorno(cls) -> "GraphClient":
        return cls(os.environ["SP_TENANT_ID"], os.environ["SP_CLIENT_ID"], os.environ["SP_CLIENT_SECRET"])

    def _token(self) -> str:
        r = self._app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in r:
            raise RuntimeError(f"No se obtuvo token de Graph: {r.get('error_description')}")
        return r["access_token"]

    def get(self, url: str) -> dict:
        for intento in range(4):
            resp = self._http.get(url, headers={"Authorization": f"Bearer {self._token()}",
                                                "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"})
            if resp.status_code in (429, 503):  # throttling: respetar Retry-After
                import time
                time.sleep(int(resp.headers.get("Retry-After", 2 ** intento)))
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return {}

    def items(self, site_id: str, lista: str, delta_link: str | None = None) -> tuple[Iterator[dict], dict]:
        """Itera ítems (con fields). El dict devuelto se completa con 'deltaLink' al terminar."""
        estado: dict = {}
        url = delta_link or f"{GRAPH}/sites/{site_id}/lists/{lista}/items/delta?expand=fields"

        def gen():
            nonlocal url
            while url:
                pagina = self.get(url)
                yield from pagina.get("value", [])
                url = pagina.get("@odata.nextLink")
                if "@odata.deltaLink" in pagina:
                    estado["deltaLink"] = pagina["@odata.deltaLink"]

        return gen(), estado


def _ym(valor) -> str | None:
    if not valor:
        return None
    return str(valor)[:7]  # '2026-09-01T03:00:00Z' -> '2026-09'


def mapear_proyecto(item: dict) -> dict:
    f = item.get("fields", {})
    p = {clave: f.get(interno) for interno, clave in MAPEO_PROYECTO.items()}
    for campo, tabla in NORMALIZA.items():
        if p.get(campo) in tabla:
            p[campo] = tabla[p[campo]]
    p["fechaInicio"] = _ym(p["fechaInicio"])
    p["simulable"] = bool(p.get("simulable"))
    for k in ("potencia", "hhParque", "hhEt", "hhLinea", "hhProy", "factorSolapamiento"):
        if p.get(k) not in (None, ""):
            p[k] = float(p[k])
    if p.get("duracion") not in (None, ""):
        p["duracion"] = int(float(p["duracion"]))
    p["id"] = int(item["id"])
    return p


def validar_proyecto(p: dict) -> list[str]:
    errores = []
    if p.get("tipoCliente") not in ("DPI", "DNN", "O&M"):
        errores.append(f"Tipo Cliente desconocido: {p.get('tipoCliente')!r}")
    if not p.get("fechaInicio"):
        errores.append("Sin Fecha Inicio")
    if p.get("tipoCliente") == "DNN" and p.get("nivelDNN") not in ("DNN Cat1", "DNN Cat2"):
        errores.append("DNN sin Nivel DNN válido")
    fs = p.get("factorSolapamiento")
    if fs is not None and not 0 <= fs <= 1:
        errores.append(f"Factor Solapamiento fuera de rango: {fs}")
    if p.get("duracion") is not None and p["duracion"] < 1:
        errores.append(f"Duración inválida: {p['duracion']}")
    return errores


def sincronizar(cn, cliente: GraphClient | None = None) -> dict:
    """Sincroniza DIM_Proyecto y DIM_Curvas hacia la base local. Devuelve un resumen."""
    from . import repositorio

    cliente = cliente or GraphClient.desde_entorno()
    site = os.environ["SP_SITE_ID"]
    lista_p = os.environ.get("SP_LIST_PROYECTOS", "DIM_Proyecto")
    lista_c = os.environ.get("SP_LIST_CURVAS", "DIM_Curvas")
    inicio = datetime.now(timezone.utc).isoformat()
    prev = cn.execute("SELECT delta_link FROM sync_log WHERE origen=? AND error IS NULL AND delta_link IS NOT NULL "
                      "ORDER BY id DESC LIMIT 1", (lista_p,)).fetchone()

    leidos = actualizados = borrados = 0
    rechazados: list[dict] = []
    it, estado = cliente.items(site, lista_p, prev["delta_link"] if prev else None)
    with cn:
        for item in it:
            leidos += 1
            if "deleted" in item:  # el delta informa bajas
                cn.execute("DELETE FROM dim_proyecto WHERE sp_item_id = ?", (item["id"],))
                borrados += 1
                continue
            p = mapear_proyecto(item)
            errores = validar_proyecto(p)
            if errores:
                rechazados.append({"id": item["id"], "proyecto": p.get("proyecto"), "errores": errores})
                continue
            repositorio.upsert_proyecto(cn, p, sp_item_id=item["id"], sp_modified=item.get("lastModifiedDateTime"))
            actualizados += 1

    # Las curvas cambian poco: lectura completa y reemplazo transaccional.
    curvas, _ = cliente.items(site, lista_c)
    filas = []
    for item in curvas:
        f = item.get("fields", {})
        c = {clave: f.get(interno) for interno, clave in MAPEO_CURVA.items()}
        filas.append((c["tipoCurva"], int(c["mes"]), c["especialidad"], float(c["factor"])))
    if filas:
        with cn:
            cn.execute("DELETE FROM dim_curva")
            cn.executemany("INSERT INTO dim_curva VALUES (?,?,?,?)", filas)

    with cn:
        cn.execute("INSERT INTO sync_log (origen, inicio_ts, fin_ts, leidos, actualizados, delta_link) VALUES (?,?,?,?,?,?)",
                   (lista_p, inicio, datetime.now(timezone.utc).isoformat(), leidos, actualizados, estado.get("deltaLink")))
    return {"leidos": leidos, "actualizados": actualizados, "borrados": borrados,
            "rechazados": rechazados, "curvas": len(filas)}
