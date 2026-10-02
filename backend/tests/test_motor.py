"""Tests del motor de capacidad (stdlib unittest; se corren con `python -m unittest`)."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from app import motor
from app.datos_ejemplo import dataset

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
        ppsdv = next(p for p in self.d["proyectos"] if p["proyecto"] == "PPSDV")
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

    def test_escenario_sumar_electricos_baja_exceso(self):
        base = motor.calcular(self.d)["cuellos"]["Eléctricos"]["hhExcedidas"]
        esc = {"capacidad": {"dotacion": {"Eléctricos": 18}}}
        nuevo = motor.calcular(self.d, esc)["cuellos"]["Eléctricos"]["hhExcedidas"]
        self.assertLess(nuevo, base)

    def test_mejor_inicio_no_empeora(self):
        r = motor.mejor_inicio(self.d, None, 8)
        actual = next(x for x in r["pruebas"] if x["desplazamiento"] == 0)
        self.assertLessEqual(r["mejor"]["hhExcedidas"], actual["hhExcedidas"])


@unittest.skipIf(shutil.which("node") is None, "node no disponible")
class ParidadJavaScript(unittest.TestCase):
    """El prototipo calcula en el navegador con engine.js: debe dar lo mismo que Python."""

    def _js(self, escenario):
        script = (
            "const E=require(process.argv[1]);const d=require(process.argv[2]);"
            "const r=E.calcular(d,JSON.parse(process.argv[3]));"
            "console.log(JSON.stringify({kpis:r.kpis,ocupacion:r.ocupacion,pareto:r.pareto,cuellos:r.cuellos}));"
        )
        out = subprocess.run(
            ["node", "-e", script, str(RAIZ / "prototipo" / "engine.js"),
             str(RAIZ / "data" / "sample_data.json"), json.dumps(escenario)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(out.stdout)

    def _comparar(self, escenario):
        d = json.loads((RAIZ / "data" / "sample_data.json").read_text(encoding="utf-8"))
        py = motor.calcular(d, escenario)
        js = self._js(escenario)
        for clave in ("hhExcedidas", "hhForecastHorizonte", "hhForecastTotal"):
            self.assertAlmostEqual(py["kpis"][clave], js["kpis"][clave], places=6)
        self.assertEqual(py["kpis"]["maxOcupacion"]["mes"], js["kpis"]["maxOcupacion"]["mes"])
        self.assertEqual(py["kpis"]["primerMesCritico"], js["kpis"]["primerMesCritico"])
        for a, b in zip(py["ocupacion"], js["ocupacion"]):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=9)
        self.assertEqual([p["proyecto"] for p in py["pareto"]], [p["proyecto"] for p in js["pareto"]])
        for e in py["cuellos"]:
            self.assertEqual(py["cuellos"][e]["personasAdicionales"], js["cuellos"][e]["personasAdicionales"])

    def test_paridad_base(self):
        self._comparar({})

    def test_paridad_escenario(self):
        self._comparar({
            "proyectos": {"8": {"desplazamiento": 4}, "3": {"incluir": False}},
            "capacidad": {"dotacion": {"Eléctricos": 16}, "eficiencia": 0.8,
                          "eventos": [{"especialidad": "Civiles", "desde": "2027-01", "hasta": "2027-09", "delta": 2}]},
        })


if __name__ == "__main__":
    unittest.main()
