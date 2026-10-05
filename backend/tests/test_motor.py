"""Tests del motor de capacidad (stdlib unittest; se corren con `python -m unittest`)."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from app import motor
from app.datos_ejemplo import dataset as _dataset
from app.importar_csv import leer

# Dotación chica para que los proyectos del CSV generen meses críticos y los
# tests ejerciten excesos, cuellos y escenarios.
DOTACION_TEST = {"Civiles": 3, "Coordinadores": 2, "Eléctricos": 5, "Electrónicos": 1, "Mecánicos": 1}


def dataset():
    d = _dataset()
    d["capacidad"]["dotacion"] = dict(DOTACION_TEST)
    return d

RAIZ = Path(__file__).resolve().parents[2]


class ReglasDeNegocio(unittest.TestCase):
    def setUp(self):
        self.d = dataset()
        self.params = self.d["parametros"]

    def test_interpolacion_solar_muy_grande(self):
        p = {"tecnologia": "Solar", "tamano": "Muy Grande", "potencia": 300}
        self.assertEqual(motor.hh_parque_base(p, self.params), 7000)
        p["potencia"] = 500
        self.assertEqual(motor.hh_parque_base(p, self.params), 10000)
        p["potencia"] = 400
        self.assertEqual(motor.hh_parque_base(p, self.params), 8500)

    def test_componentes_ppsdv_suman_11800(self):
        ppsdv = next(p for p in self.d["proyectos"] if p["proyecto"] == "PSSDV")
        self.assertEqual(motor.tamano(ppsdv, self.params), "Muy Grande")  # 300 MW, sin Tamaño en el CSV
        comps = {c["componente"]: c for c in motor.componentes(ppsdv, self.params)}
        self.assertEqual(comps["Parque"]["hh"], 7000)
        self.assertEqual(comps["ET"]["hh"], 3000)
        self.assertEqual(comps["Línea"]["hh"], 1800)
        self.assertEqual(comps["Línea"]["curva"], "Línea AT")
        self.assertEqual(sum(c["hh"] for c in comps.values()), 11800)

    def test_ampliacion_et_y_linea_mt(self):
        p = {"tipoCliente": "DPI", "tecnologia": "Bess", "tamano": "Grande", "potencia": 100,
             "est": "Ampliación ET", "linea": "Línea MT"}
        comps = {c["componente"]: c["hh"] for c in motor.componentes(p, self.params)}
        self.assertAlmostEqual(comps["ET"], 2000 * 0.30)
        self.assertAlmostEqual(comps["Línea"], 1200 * 0.70)

    def test_curvas_suman_aproximadamente_uno(self):
        for nombre, curva in self.d["curvas"].items():
            total = sum(sum(v) for v in curva.values())
            self.assertAlmostEqual(total, 1.0, delta=0.005, msg=nombre)

    def test_factor_solapamiento_descuenta(self):
        d = dataset()
        d["proyectos"] = [dict(d["proyectos"][0], factorSolapamiento=0.6)]
        filas = motor.forecast(d["proyectos"], d["curvas"], d["parametros"])
        total = sum(f["hh"] for f in filas)
        self.assertAlmostEqual(total, 11800 * 0.6, delta=11800 * 0.6 * 0.005)

    def test_capacidad_con_eventos(self):
        cap = self.d["capacidad"]
        antes = motor.capacidad_mes(cap, motor.mes_idx("2027-02"), "Eléctricos")
        despues = motor.capacidad_mes(cap, motor.mes_idx("2027-03"), "Eléctricos")
        self.assertAlmostEqual(antes - despues, cap["hhMesPersona"] * cap["eficiencia"])

    def test_kpis_coherentes(self):
        r = motor.calcular(self.d)
        k = r["kpis"]
        # HH excedidas = suma de max(0, demanda - capacidad)
        exc = sum(max(0.0, d - c) for fd, fc in zip(r["demanda"], r["capacidad"]) for d, c in zip(fd, fc))
        self.assertAlmostEqual(k["hhExcedidas"], exc)
        self.assertGreater(k["maxOcupacion"]["valor"], 1)
        pc = k["primerMesCritico"]["mes"]
        i = r["meses"].index(pc)
        self.assertTrue(any(o > 1 for o in r["ocupacion"][i]))
        self.assertTrue(all(o <= 1 for fila in r["ocupacion"][:i] for o in fila))
        self.assertAlmostEqual(r["pareto"][-1]["pctAcum"], 1.0)

    def test_indicadores_desde_mes_actual(self):
        """Los meses anteriores a kpiDesde se muestran pero no cuentan como exceso ni como mes crítico."""
        todo = motor.calcular(self.d)
        d = dataset()
        d["horizonte"]["kpiDesde"] = "2026-10"
        r = motor.calcular(d)
        self.assertEqual(r["meses"][0], "2026-01")
        self.assertEqual(r["kpiDesde"], "2026-10")
        self.assertEqual(r["ocupacion"], todo["ocupacion"])          # la matriz no cambia
        i0 = r["meses"].index("2026-10")
        exc = sum(max(0.0, dm - c) for fd, fc in zip(r["demanda"][i0:], r["capacidad"][i0:]) for dm, c in zip(fd, fc))
        self.assertAlmostEqual(r["kpis"]["hhExcedidas"], exc)
        self.assertGreaterEqual(r["kpis"]["primerMesCritico"]["mes"], "2026-10")
        self.assertLessEqual(r["kpis"]["hhExcedidas"], todo["kpis"]["hhExcedidas"])

    def test_horizonte_se_extiende(self):
        base = motor.calcular(self.d)
        self.assertEqual(len(base["meses"]), self.d["horizonte"]["meses"])
        # PSSDV (id 1, 12 meses desde feb-27) movido 30 meses: arranca ago-29 y termina jul-30
        r = motor.calcular(self.d, {"proyectos": {"1": {"desplazamiento": 30}}})
        self.assertEqual(r["meses"][-1], "2030-07")
        self.assertAlmostEqual(r["kpis"]["hhForecastTotal"], base["kpis"]["hhForecastTotal"])
        self.assertAlmostEqual(sum(map(sum, r["demanda"])), sum(map(sum, base["demanda"])))
        d = dataset()
        d["horizonte"]["extender"] = False
        self.assertEqual(len(motor.calcular(d, {"proyectos": {"1": {"desplazamiento": 30}}})["meses"]), d["horizonte"]["meses"])

    def test_nomina_define_la_capacidad(self):
        cap = {"hhMesPersona": 140, "eficiencia": 0.85, "dotacion": {"Eléctricos": 99}, "eventos": [], "staff": [
            {"nombre": "Ana", "especialidad": "Eléctricos", "dedicacion": 1},
            {"nombre": "Luis", "especialidad": "Eléctricos", "dedicacion": 0.5},
            {"nombre": "Eva", "especialidad": "Eléctricos", "desde": "2027-03"},
            {"nombre": "Juan", "especialidad": "Eléctricos", "hasta": "2026-12"},
            {"nombre": "Sol", "especialidad": "Civiles"},
        ]}
        m = motor.mes_idx
        self.assertEqual(motor.personas_base(cap, m("2026-11"), "Eléctricos"), 2.5)   # Ana + Luis/2 + Juan; dotación 99 ignorada
        self.assertEqual(motor.personas_base(cap, m("2027-01"), "Eléctricos"), 1.5)   # Juan ya no está
        self.assertEqual(motor.personas_base(cap, m("2027-03"), "Eléctricos"), 2.5)   # ingresa Eva
        cap["eventos"] = [{"especialidad": "Eléctricos", "desde": "2027-01", "hasta": None, "delta": 2}]
        self.assertAlmostEqual(motor.capacidad_mes(cap, m("2027-01"), "Eléctricos"), 3.5 * 140 * 0.85)
        cap["staff"][0]["simulado"] = False                                               # Ana destildada: no suma
        self.assertEqual(motor.personas_base(cap, m("2027-01"), "Eléctricos"), 0.5)
        cap["staff"] = []
        self.assertEqual(motor.personas_base(cap, m("2027-01"), "Eléctricos"), 99)        # sin nómina: dotación

    def test_sensibilidad_dnn(self):
        d = dataset()
        dnn = next(p for p in d["proyectos"] if p["proyecto"] == "PEDAN")  # DNN Cat1: 3 meses desde sep-26
        base = motor.forecast([dnn], d["curvas"], d["parametros"])
        con = motor.forecast([dict(dnn, sensibilidades=2)], d["curvas"], d["parametros"])
        meses = sorted({motor.mes_str(f["mes"]) for f in con})
        # original sep-nov 26; termina nov-26 → la 1.ª arranca feb-27 (3 meses después) → la 2.ª may-27
        self.assertEqual(meses, ["2026-09", "2026-10", "2026-11", "2027-02", "2027-03", "2027-04", "2027-07", "2027-08", "2027-09"])
        self.assertAlmostEqual(sum(f["hh"] for f in con), 3 * sum(f["hh"] for f in base))
        # solo DNN: en un DPI no tiene efecto
        dpi = d["proyectos"][0]
        self.assertEqual(len(motor.forecast([dict(dpi, sensibilidades=2)], d["curvas"], d["parametros"])),
                         len(motor.forecast([dpi], d["curvas"], d["parametros"])))

    def test_tecnologia_otro_plan_manual(self):
        d = dataset()
        otro = {"id": 99, "proyecto": "HIDRO", "tipoCliente": "DPI", "tecnologia": "Otro", "fechaInicio": "2027-03",
                "factorSolapamiento": 0.5,  # no se aplica a «Otro»
                "planManual": {"unidad": "personas", "meses": 3,
                               "valores": {"Eléctricos": [1, 2, 2], "Civiles": [0.5, 0.5, 0]}}}
        hp = 140 * 0.85
        params = {**d["parametros"], "hhPersonaMes": hp}
        self.assertAlmostEqual(motor.componentes(otro, params)[0]["hh"], 6 * hp)
        f = motor.forecast([otro], d["curvas"], params)
        por_mes = {}
        for x in f:
            por_mes[(motor.mes_str(x["mes"]), x["especialidad"])] = por_mes.get((motor.mes_str(x["mes"]), x["especialidad"]), 0) + x["hh"]
        self.assertAlmostEqual(por_mes[("2027-04", "Eléctricos")], 2 * hp)
        self.assertAlmostEqual(por_mes[("2027-03", "Civiles")], 0.5 * hp)
        self.assertAlmostEqual(sum(x["hh"] for x in f), 6 * hp)            # sin solapamiento
        # en HH
        otro_hh = dict(otro, planManual={"unidad": "hh", "meses": 2, "valores": {"Estudios": [100, 50]}})
        self.assertAlmostEqual(sum(x["hh"] for x in motor.forecast([otro_hh], d["curvas"], params)), 150)
        # duración: estira conservando HH
        largo = motor.forecast([dict(otro, duracion=6)], d["curvas"], params)
        self.assertEqual(len({x["mes"] for x in largo}), 6)
        self.assertAlmostEqual(sum(x["hh"] for x in largo), 6 * hp)
        # sensibilidad DNN sobre un «Otro»
        dnn = dict(otro, tipoCliente="DNN", sensibilidades=1)
        self.assertEqual([b for b in motor.bloques(dnn, d["curvas"], params)], [(0, 3), (5, 3)])
        # calcular usa HH/persona × eficiencia de la capacidad
        d2 = dataset(); d2["proyectos"] = [otro]
        r = motor.calcular(d2)
        self.assertAlmostEqual(r["kpis"]["hhForecastTotal"], 6 * d2["capacidad"]["hhMesPersona"] * d2["capacidad"]["eficiencia"])

    def test_escenario_sumar_electricos_baja_exceso(self):
        base = motor.calcular(self.d)["cuellos"]["Eléctricos"]["hhExcedidas"]
        esc = {"capacidad": {"dotacion": {"Eléctricos": 9}}}
        nuevo = motor.calcular(self.d, esc)["cuellos"]["Eléctricos"]["hhExcedidas"]
        self.assertLess(nuevo, base)

    def test_tamano_por_potencia(self):
        t = lambda tec, mw: motor.tamano({"tecnologia": tec, "potencia": mw}, self.params)
        self.assertEqual(t("Bess", 15), "Chico")
        self.assertEqual(t("Bess", 40), "Mediano")
        self.assertEqual(t("Bess", 100), "Grande")
        self.assertEqual(t("Solar", 299), "Grande")
        self.assertEqual(t("Solar", 300), "Muy Grande")
        self.assertEqual(motor.tamano({"tecnologia": "Solar", "potencia": 300, "tamano": "Chico"}, self.params), "Chico")

    def test_importar_csv(self):
        texto = ('"Proyectos","Nombre","Tipo Cliente","Nivel DNN","Tecnología","Factor Solapa","Potencia",'
                 '"Tensión POE","Est Transformadora","Linea","Fecha Inicio","Estado","Calendario Fijo","% Avance"\n'
                 '"PSSDV","Sol del Valle","DPI","N/A","Solar","1,00","300","132","Et Nueva","Línea AT",'
                 '"01/02/2027 0:00","No Iniciado","Si",\n'
                 '"PABRA","Bragado","DPI","N/A","Bess","0,43","100","33","N/A","N/A","28/01/2027 0:00","En Proceso","No",\n'
                 '"PEVI3","Villalonga III","DNN","Cat 2","Eólico","1,00","33","33","N/A","N/A","01/05/2026 0:00","En Proceso","Si",\n')
        ps, avisos = leer("\ufeff" + texto)
        self.assertEqual(avisos, [])
        a, b, c = ps
        self.assertEqual((a["est"], a["linea"], a["fechaInicio"], a["simulable"]), ("ET Nueva", "Línea AT", "2027-02", False))
        self.assertEqual((b["est"], b["linea"], b["factorSolapamiento"], b["simulable"]), (None, None, 0.43, True))
        self.assertEqual((c["nivelDNN"], c["tipoCliente"]), ("DNN Cat2", "DNN"))
        self.assertEqual(sum(x["hh"] for x in motor.componentes(a, self.params)), 11800)

    def test_importar_csv_otro(self):
        texto = ('"Proyectos","Tipo Cliente","Tecnología","Fecha Inicio","Plan Manual"\n'
                 '"PX1","DPI","otro","01/03/2027 0:00","{""unidad"":""hh"",""meses"":2,""valores"":{""Civiles"":[100,50]}}"\n'
                 '"PX2","DPI","Otro","01/03/2027 0:00",""\n')
        ps, avisos = leer(texto)
        self.assertEqual(ps[0]["tecnologia"], "Otro")
        self.assertEqual(sum(c["hh"] for c in motor.componentes(ps[0], self.params)), 150)
        self.assertEqual(avisos, ["PX2: tecnología Otro sin plan de recursos"])

    def test_reescalar_conserva_suma_y_forma(self):
        curva = [0.1, 0.2, 0.3, 0.4]
        for n in (1, 2, 3, 6, 9):
            r = motor.reescalar(curva, n)
            self.assertEqual(len(r), n)
            self.assertAlmostEqual(sum(r), 1.0)
        self.assertEqual([round(x, 9) for x in motor.reescalar(curva, 2)], [0.3, 0.7])
        self.assertEqual(motor.reescalar(curva, 4), curva)

    def test_duracion_comprime_sin_perder_hh(self):
        d = dataset()
        ppsdv = dict(d["proyectos"][0])
        self.assertEqual(motor.duracion_base(ppsdv, d["curvas"], d["parametros"]), 12)
        base = motor.forecast([ppsdv], d["curvas"], d["parametros"])
        corto = motor.forecast([dict(ppsdv, duracion=6)], d["curvas"], d["parametros"])
        self.assertAlmostEqual(sum(f["hh"] for f in base), sum(f["hh"] for f in corto), places=6)
        meses = lambda filas, comp: {f["mes"] for f in filas if f["componente"] == comp}
        self.assertEqual(len(meses(corto, "Parque")), 6)       # Solar 12 m -> 6 m
        self.assertEqual(len(meses(corto, "ET")), 5)           # ET Nueva 10 m -> 5 m
        self.assertEqual(len(meses(corto, "Línea")), 5)        # Línea AT 9 m -> 4,5 -> 5 m
        pico = lambda filas: max(sum(f["hh"] for f in filas if f["mes"] == m) for m in {f["mes"] for f in filas})
        self.assertGreater(pico(corto), pico(base))

    def test_duracion_estira(self):
        d = dataset()
        largo = motor.forecast([dict(d["proyectos"][0], duracion=18)], d["curvas"], d["parametros"])
        self.assertEqual(len({f["mes"] for f in largo if f["componente"] == "Parque"}), 18)

    def test_mejor_inicio_no_empeora(self):
        r = motor.mejor_inicio(self.d, None, 8)
        actual = next(x for x in r["pruebas"] if x["desplazamiento"] == 0)
        self.assertLessEqual(r["mejor"]["hhExcedidas"], actual["hhExcedidas"])


@unittest.skipIf(shutil.which("node") is None, "node no disponible")
class ParidadJavaScript(unittest.TestCase):
    """El prototipo calcula en el navegador con engine.js: debe dar lo mismo que Python."""

    def _js(self, escenario, ruta_datos=None):
        script = (
            "const E=require(process.argv[1]);const d=require(process.argv[2]);"
            "const r=E.calcular(d,JSON.parse(process.argv[3]));"
            "console.log(JSON.stringify({kpis:r.kpis,ocupacion:r.ocupacion,pareto:r.pareto,cuellos:r.cuellos}));"
        )
        out = subprocess.run(
            ["node", "-e", script, str(RAIZ / "prototipo" / "engine.js"),
             str(ruta_datos or RAIZ / "data" / "sample_data.json"), json.dumps(escenario)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(out.stdout)

    def _comparar(self, escenario):
        d = json.loads((RAIZ / "data" / "sample_data.json").read_text(encoding="utf-8"))
        escenario = {**escenario, "capacidad": {"dotacion": DOTACION_TEST, **escenario.get("capacidad", {})}}
        py = motor.calcular(d, escenario)
        js = self._js(escenario)
        for clave in ("hhExcedidas", "hhForecastHorizonte", "hhForecastTotal"):
            self.assertAlmostEqual(py["kpis"][clave], js["kpis"][clave], places=6)
        self.assertEqual(py["kpis"]["maxOcupacion"]["mes"], js["kpis"]["maxOcupacion"]["mes"])
        self.assertEqual(py["kpis"]["primerMesCritico"], js["kpis"]["primerMesCritico"])
        for a, b in zip(py["ocupacion"], js["ocupacion"]):
            for x, y in zip(a, b):
                if y is None:  # JSON no tiene Infinity: JS lo serializa como null
                    self.assertEqual(x, float("inf"))
                else:
                    self.assertAlmostEqual(x, y, places=9)
        self.assertEqual([p["proyecto"] for p in py["pareto"]], [p["proyecto"] for p in js["pareto"]])
        for e in py["cuellos"]:
            self.assertEqual(py["cuellos"][e]["personasAdicionales"], js["cuellos"][e]["personasAdicionales"])

    def test_paridad_kpi_desde(self):
        import tempfile
        d = json.loads((RAIZ / "data" / "sample_data.json").read_text(encoding="utf-8"))
        d["horizonte"]["kpiDesde"] = "2026-10"
        esc = {"capacidad": {"dotacion": DOTACION_TEST}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        js = self._js(esc, f.name)
        py = motor.calcular(d, esc)
        self.assertAlmostEqual(py["kpis"]["hhExcedidas"], js["kpis"]["hhExcedidas"], places=6)
        self.assertEqual(py["kpis"]["primerMesCritico"], js["kpis"]["primerMesCritico"])
        for e in py["cuellos"]:
            self.assertEqual(py["cuellos"][e]["personasAdicionales"], js["cuellos"][e]["personasAdicionales"])

    def test_paridad_nomina(self):
        staff = [{"nombre": f"P{i}", "especialidad": e, "dedicacion": 0.5 if i % 3 == 0 else 1,
                  "desde": "2027-02" if i % 4 == 0 else None, "hasta": "2027-08" if i % 5 == 0 else None,
                  "simulado": i != 2}
                 for i, e in enumerate(["Civiles", "Eléctricos", "Eléctricos", "Coordinadores", "Mecánicos",
                                        "Electrónicos", "Eléctricos", "Civiles", "Eléctricos", "Civiles"])]
        self._comparar({"capacidad": {"staff": staff}})

    def test_paridad_otro(self):
        import tempfile
        d = json.loads((RAIZ / "data" / "sample_data.json").read_text(encoding="utf-8"))
        d["proyectos"].append({"id": 99, "proyecto": "HIDRO", "tipoCliente": "DNN", "tecnologia": "Otro", "fechaInicio": "2027-02",
                               "sensibilidades": 1, "duracion": 7,
                               "planManual": {"unidad": "personas", "meses": 4,
                                              "valores": {"Eléctricos": [1, 2, 2.5, 1], "Estudios": [1, 1, 0, 0]}}})
        d["proyectos"].append({"id": 98, "proyecto": "OTROHH", "tipoCliente": "DPI", "tecnologia": "Otro", "fechaInicio": "2026-11",
                               "planManual": {"unidad": "hh", "meses": 3, "valores": {"Civiles": [300, 200, 100]}}})
        esc = {"capacidad": {"dotacion": DOTACION_TEST, "eficiencia": 0.8}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        js = self._js(esc, f.name)
        py = motor.calcular(d, esc)
        for clave in ("hhExcedidas", "hhForecastTotal", "hhForecastHorizonte"):
            self.assertAlmostEqual(py["kpis"][clave], js["kpis"][clave], places=6)
        self.assertEqual([x["proyecto"] for x in py["pareto"]], [x["proyecto"] for x in js["pareto"]])

    def test_paridad_base(self):
        self._comparar({})

    def test_paridad_escenario(self):
        self._comparar({
            "proyectos": {"8": {"desplazamiento": 4}, "3": {"incluir": False},
                          "1": {"duracion": 7, "desplazamiento": 26}, "2": {"duracion": 20}, "9": {"duracion": 4},
                          "13": {"sensibilidades": 2, "duracion": 5}, "15": {"sensibilidades": 1}},
            "capacidad": {"dotacion": {"Eléctricos": 16}, "eficiencia": 0.8,
                          "eventos": [{"especialidad": "Civiles", "desde": "2027-01", "hasta": "2027-09", "delta": 2}]},
        })


if __name__ == "__main__":
    unittest.main()
