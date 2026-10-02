"""Prueba de humo de la API (se omite si FastAPI no está instalado)."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest


@unittest.skipIf(importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("httpx") is None,
                 "fastapi/httpx no instalados")
class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["CAPACIDAD_DB"] = os.path.join(cls.tmp.name, "test.db")
        from fastapi.testclient import TestClient

        from app import main
        main.DB = os.environ["CAPACIDAD_DB"]
        cls.c = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_flujo_escenario(self):
        base = self.c.post("/api/simular", json={"cambios": {}}).json()["kpis"]
        r = self.c.post("/api/escenarios", json={
            "nombre": "+4 eléctricos", "cambios": {"capacidad": {"dotacion": {"Eléctricos": 18}}}})
        self.assertEqual(r.status_code, 201)
        esc = r.json()
        res = self.c.get(f"/api/escenarios/{esc['id']}/resultado").json()["kpis"]
        self.assertLess(res["hhExcedidas"], base["hhExcedidas"])
        cmp_ = self.c.get(f"/api/comparar?ids=0,{esc['id']}").json()
        self.assertEqual(len(cmp_), 2)

    def test_dataset_roundtrip(self):
        """La base SQLite devuelve exactamente el mismo resultado que el dataset en memoria."""
        from app import motor
        from app.datos_ejemplo import dataset
        d = self.c.get("/api/datos").json()
        self.assertAlmostEqual(motor.calcular(d)["kpis"]["hhExcedidas"],
                               motor.calcular(dataset())["kpis"]["hhExcedidas"], places=6)

    def test_duracion_en_escenario(self):
        base = self.c.post("/api/simular", json={"cambios": {}}).json()["kpis"]
        corto = self.c.post("/api/simular", json={"cambios": {"proyectos": {"2": {"duracion": 6}}}}).json()["kpis"]
        self.assertAlmostEqual(base["hhForecastTotal"], corto["hhForecastTotal"], places=6)
        self.assertNotAlmostEqual(base["hhExcedidas"], corto["hhExcedidas"], places=2)

    def test_parametros_cambian_hh(self):
        par = self.c.get("/api/parametros").json()["parametros"]
        antes = self.c.post("/api/simular", json={"cambios": {}}).json()["kpis"]["hhForecastTotal"]
        par["parque"]["Solar|Muy Grande"] = [[300, 7000], [500, 12000]]
        r = self.c.put("/api/parametros", json=par)
        self.assertEqual(r.status_code, 200, r.text)
        despues = self.c.post("/api/simular", json={"cambios": {}}).json()["kpis"]["hhForecastTotal"]
        self.assertGreater(despues, antes)
        par["parque"]["Solar|Muy Grande"] = [[300, -1]]
        self.assertEqual(self.c.put("/api/parametros", json=par).status_code, 422)
        par["parque"]["Solar|Muy Grande"] = [[300, 7000], [500, 10000]]
        self.assertEqual(self.c.put("/api/parametros", json=par).status_code, 200)

    def test_curva_valida_y_normaliza(self):
        original = self.c.get("/api/parametros").json()["curvas"]["Línea MT"]
        self.addCleanup(lambda: self.c.put("/api/curvas/Línea MT", json=original))
        mala = {"Eléctricos": [0.5, 0.7]}
        self.assertEqual(self.c.put("/api/curvas/Línea MT", json=mala).status_code, 422)
        r = self.c.put("/api/curvas/Línea MT?normalizar=true", json=mala).json()
        self.assertAlmostEqual(r["suma"], 1.0)
        self.assertEqual(r["meses"], 2)
        curvas = self.c.get("/api/parametros").json()["curvas"]
        self.assertEqual(list(curvas["Línea MT"]), ["Eléctricos"])
        self.assertEqual(self.c.put("/api/curvas/Solar", json={"Pintores": [1]}).status_code, 422)

    def test_mejor_inicio_y_detalle(self):
        r = self.c.get("/api/proyectos/8/mejor-inicio").json()
        self.assertIn("mejor", r)
        det = self.c.get("/api/detalle", params={"mes": "2027-03", "especialidad": "Eléctricos"}).json()
        self.assertTrue(det and det[0]["hh"] >= det[-1]["hh"])


if __name__ == "__main__":
    unittest.main()
