// Generado por backend/app/datos_ejemplo.py — datos ilustrativos.
window.SAMPLE_DATA = {
 "meta": {
  "origen": "ejemplo",
  "nota": "Datos ilustrativos, no reales"
 },
 "horizonte": {
  "desde": "2026-10",
  "meses": 24
 },
 "especialidades": [
  "Civiles",
  "Coordinadores",
  "Eléctricos",
  "Electrónicos",
  "Mecánicos"
 ],
 "parametros": {
  "parque": {
   "Solar|Chico": [
    [
     1,
     800
    ],
    [
     20,
     1500
    ]
   ],
   "Solar|Mediano": [
    [
     20,
     1500
    ],
    [
     100,
     3500
    ]
   ],
   "Solar|Grande": [
    [
     100,
     3500
    ],
    [
     300,
     7000
    ]
   ],
   "Solar|Muy Grande": [
    [
     300,
     7000
    ],
    [
     500,
     10000
    ]
   ],
   "Bess|Chico": [
    [
     1,
     600
    ],
    [
     20,
     1200
    ]
   ],
   "Bess|Mediano": [
    [
     20,
     1200
    ],
    [
     100,
     3000
    ]
   ],
   "Bess|Grande": [
    [
     100,
     3000
    ],
    [
     250,
     5500
    ]
   ],
   "Bess|Muy Grande": [
    [
     250,
     5500
    ],
    [
     500,
     8500
    ]
   ],
   "Eólico|Chico": [
    [
     1,
     1000
    ],
    [
     30,
     2000
    ]
   ],
   "Eólico|Mediano": [
    [
     30,
     2000
    ],
    [
     100,
     4500
    ]
   ],
   "Eólico|Grande": [
    [
     100,
     4500
    ],
    [
     300,
     8500
    ]
   ],
   "Eólico|Muy Grande": [
    [
     300,
     8500
    ],
    [
     600,
     13000
    ]
   ],
   "Termico|Chico": [
    [
     1,
     1200
    ],
    [
     50,
     2500
    ]
   ],
   "Termico|Mediano": [
    [
     50,
     2500
    ],
    [
     150,
     5000
    ]
   ],
   "Termico|Grande": [
    [
     150,
     5000
    ],
    [
     400,
     9000
    ]
   ],
   "Termico|Muy Grande": [
    [
     400,
     9000
    ],
    [
     800,
     14000
    ]
   ]
  },
  "et": {
   "Chico": 500,
   "Mediano": 1000,
   "Grande": 2000,
   "Muy Grande": 3000
  },
  "factorAmpliacionET": 0.3,
  "linea": {
   "Chico": 300,
   "Mediano": 600,
   "Grande": 1200,
   "Muy Grande": 1800
  },
  "factorLineaMT": 0.7,
  "factorDNN": {
   "DNN Cat1": 0.06,
   "DNN Cat2": 0.15
  },
  "factorOM": 0.08
 },
 "capacidad": {
  "hhMesPersona": 140,
  "eficiencia": 0.85,
  "dotacion": {
   "Civiles": 8,
   "Coordinadores": 6,
   "Eléctricos": 14,
   "Electrónicos": 4,
   "Mecánicos": 5
  },
  "subcontratoHH": {},
  "eventos": [
   {
    "especialidad": "Eléctricos",
    "desde": "2027-03",
    "hasta": null,
    "delta": -1,
    "nota": "Jubilación prevista"
   }
  ]
 },
 "curvas": {
  "Solar": {
   "Civiles": [
    0.0176,
    0.0276,
    0.0375,
    0.0422,
    0.039,
    0.0297,
    0.0194,
    0.0118,
    0.0078,
    0.0062,
    0.0057,
    0.0055
   ],
   "Coordinadores": [
    0.0039,
    0.0053,
    0.0084,
    0.0136,
    0.0198,
    0.0241,
    0.0241,
    0.0198,
    0.0136,
    0.0084,
    0.0053,
    0.0039
   ],
   "Eléctricos": [
    0.0089,
    0.01,
    0.0131,
    0.0204,
    0.0334,
    0.0498,
    0.0629,
    0.0655,
    0.0559,
    0.0398,
    0.0249,
    0.0154
   ],
   "Electrónicos": [
    0.0022,
    0.0023,
    0.0024,
    0.0029,
    0.0043,
    0.007,
    0.011,
    0.015,
    0.017,
    0.0158,
    0.0122,
    0.008
   ],
   "Mecánicos": [
    0.0023,
    0.0029,
    0.0042,
    0.0069,
    0.0107,
    0.0146,
    0.0165,
    0.0152,
    0.0116,
    0.0076,
    0.0046,
    0.003
   ]
  },
  "Bess": {
   "Civiles": [
    0.0153,
    0.0263,
    0.0335,
    0.0302,
    0.0195,
    0.0103,
    0.0059,
    0.0047,
    0.0044
   ],
   "Coordinadores": [
    0.0054,
    0.0088,
    0.0168,
    0.0276,
    0.0329,
    0.0276,
    0.0168,
    0.0088,
    0.0054
   ],
   "Eléctricos": [
    0.012,
    0.0148,
    0.0251,
    0.048,
    0.0764,
    0.088,
    0.0712,
    0.0424,
    0.0221
   ],
   "Electrónicos": [
    0.006,
    0.0062,
    0.0074,
    0.0123,
    0.0236,
    0.0384,
    0.0454,
    0.0378,
    0.023
   ],
   "Mecánicos": [
    0.0032,
    0.0045,
    0.0084,
    0.0152,
    0.0212,
    0.0208,
    0.0145,
    0.0079,
    0.0043
   ]
  },
  "Eólico": {
   "Civiles": [
    0.0161,
    0.0234,
    0.0315,
    0.0381,
    0.0406,
    0.0381,
    0.0315,
    0.0234,
    0.0161,
    0.0108,
    0.0077,
    0.0062,
    0.0056,
    0.0054,
    0.0053
   ],
   "Coordinadores": [
    0.003,
    0.0038,
    0.0053,
    0.0078,
    0.0114,
    0.0153,
    0.0185,
    0.0197,
    0.0185,
    0.0153,
    0.0114,
    0.0078,
    0.0053,
    0.0038,
    0.003
   ],
   "Eléctricos": [
    0.0053,
    0.0057,
    0.0067,
    0.0088,
    0.0129,
    0.0191,
    0.0269,
    0.0344,
    0.039,
    0.039,
    0.0344,
    0.0269,
    0.0191,
    0.0129,
    0.0088
   ],
   "Electrónicos": [
    0.0009,
    0.0009,
    0.0009,
    0.001,
    0.0012,
    0.0016,
    0.0024,
    0.0035,
    0.0049,
    0.0061,
    0.0068,
    0.0066,
    0.0057,
    0.0043,
    0.003
   ],
   "Mecánicos": [
    0.0037,
    0.0042,
    0.0054,
    0.0077,
    0.0115,
    0.0165,
    0.0217,
    0.0254,
    0.0262,
    0.0238,
    0.0192,
    0.0139,
    0.0094,
    0.0064,
    0.0047
   ]
  },
  "Termico": {
   "Civiles": [
    0.0107,
    0.0156,
    0.021,
    0.0254,
    0.0271,
    0.0254,
    0.021,
    0.0156,
    0.0107,
    0.0072,
    0.0052,
    0.0042,
    0.0037,
    0.0036,
    0.0035
   ],
   "Coordinadores": [
    0.003,
    0.0038,
    0.0053,
    0.0078,
    0.0114,
    0.0153,
    0.0185,
    0.0197,
    0.0185,
    0.0153,
    0.0114,
    0.0078,
    0.0053,
    0.0038,
    0.003
   ],
   "Eléctricos": [
    0.0044,
    0.0048,
    0.0056,
    0.0074,
    0.0107,
    0.0159,
    0.0224,
    0.0287,
    0.0325,
    0.0325,
    0.0287,
    0.0224,
    0.0159,
    0.0107,
    0.0074
   ],
   "Electrónicos": [
    0.0018,
    0.0018,
    0.0019,
    0.002,
    0.0024,
    0.0033,
    0.0048,
    0.0071,
    0.0098,
    0.0123,
    0.0136,
    0.0132,
    0.0114,
    0.0087,
    0.0061
   ],
   "Mecánicos": [
    0.0056,
    0.0063,
    0.0081,
    0.0116,
    0.0173,
    0.0248,
    0.0325,
    0.0381,
    0.0394,
    0.0358,
    0.0288,
    0.0209,
    0.0142,
    0.0096,
    0.0071
   ]
  },
  "ET Nueva": {
   "Civiles": [
    0.0177,
    0.0295,
    0.0391,
    0.0391,
    0.0295,
    0.0177,
    0.0099,
    0.0065,
    0.0055,
    0.0053
   ],
   "Coordinadores": [
    0.0032,
    0.0048,
    0.0086,
    0.0144,
    0.019,
    0.019,
    0.0144,
    0.0086,
    0.0048,
    0.0032
   ],
   "Eléctricos": [
    0.0148,
    0.0175,
    0.0265,
    0.0477,
    0.0794,
    0.1052,
    0.1052,
    0.0794,
    0.0477,
    0.0265
   ],
   "Electrónicos": [
    0.0027,
    0.0027,
    0.0031,
    0.0045,
    0.0079,
    0.0137,
    0.0191,
    0.0202,
    0.0161,
    0.01
   ],
   "Mecánicos": [
    0.0014,
    0.0019,
    0.0032,
    0.0057,
    0.0086,
    0.0099,
    0.0086,
    0.0057,
    0.0032,
    0.0019
   ]
  },
  "Ampliación ET": {
   "Civiles": [
    0.0267,
    0.0488,
    0.0416,
    0.0181,
    0.0081,
    0.0067
   ],
   "Coordinadores": [
    0.0059,
    0.0144,
    0.0298,
    0.0298,
    0.0144,
    0.0059
   ],
   "Eléctricos": [
    0.0279,
    0.0482,
    0.1242,
    0.1973,
    0.1442,
    0.0582
   ],
   "Electrónicos": [
    0.0045,
    0.0052,
    0.0108,
    0.0261,
    0.0335,
    0.0199
   ],
   "Mecánicos": [
    0.0025,
    0.0053,
    0.0128,
    0.0162,
    0.0095,
    0.0037
   ]
  },
  "Línea MT": {
   "Civiles": [
    0.0623,
    0.1138,
    0.0971,
    0.0423,
    0.0189,
    0.0156
   ],
   "Coordinadores": [
    0.0059,
    0.0144,
    0.0298,
    0.0298,
    0.0144,
    0.0059
   ],
   "Eléctricos": [
    0.0232,
    0.0402,
    0.1035,
    0.1644,
    0.1202,
    0.0485
   ],
   "Electrónicos": [
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0
   ],
   "Mecánicos": [
    0.0025,
    0.0053,
    0.0128,
    0.0162,
    0.0095,
    0.0037
   ]
  },
  "Línea AT": {
   "Civiles": [
    0.0407,
    0.07,
    0.0895,
    0.0804,
    0.052,
    0.0274,
    0.0158,
    0.0124,
    0.0118
   ],
   "Coordinadores": [
    0.0036,
    0.0059,
    0.0112,
    0.0184,
    0.0219,
    0.0184,
    0.0112,
    0.0059,
    0.0036
   ],
   "Eléctricos": [
    0.0135,
    0.0167,
    0.0282,
    0.0539,
    0.0859,
    0.099,
    0.0801,
    0.0477,
    0.0249
   ],
   "Electrónicos": [
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0
   ],
   "Mecánicos": [
    0.0016,
    0.0023,
    0.0042,
    0.0076,
    0.0106,
    0.0104,
    0.0073,
    0.0039,
    0.0021
   ]
  },
  "DNN Cat1": {
   "Civiles": [
    0.0781,
    0.058,
    0.0139
   ],
   "Coordinadores": [
    0.0522,
    0.1956,
    0.0522
   ],
   "Eléctricos": [
    0.0389,
    0.2,
    0.1111
   ],
   "Electrónicos": [
    0.0046,
    0.0174,
    0.028
   ],
   "Mecánicos": [
    0.0202,
    0.0946,
    0.0352
   ]
  },
  "DNN Cat2": {
   "Civiles": [
    0.0203,
    0.035,
    0.0447,
    0.0402,
    0.026,
    0.0137,
    0.0079,
    0.0062,
    0.0059
   ],
   "Coordinadores": [
    0.0089,
    0.0146,
    0.0281,
    0.046,
    0.0548,
    0.046,
    0.0281,
    0.0146,
    0.0089
   ],
   "Eléctricos": [
    0.0105,
    0.013,
    0.0219,
    0.042,
    0.0668,
    0.077,
    0.0623,
    0.0371,
    0.0193
   ],
   "Electrónicos": [
    0.0015,
    0.0015,
    0.0019,
    0.0031,
    0.0059,
    0.0096,
    0.0114,
    0.0095,
    0.0057
   ],
   "Mecánicos": [
    0.0048,
    0.0068,
    0.0126,
    0.0229,
    0.0318,
    0.0312,
    0.0218,
    0.0118,
    0.0064
   ]
  },
  "O&M": {
   "Civiles": [
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083,
    0.0083
   ],
   "Coordinadores": [
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167,
    0.0167
   ],
   "Eléctricos": [
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333,
    0.0333
   ],
   "Electrónicos": [
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125
   ],
   "Mecánicos": [
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125,
    0.0125
   ]
  }
 },
 "proyectos": [
  {
   "id": 1,
   "proyecto": "PPSDV",
   "tipoCliente": "DPI",
   "tecnologia": "Solar",
   "potencia": 300,
   "tamano": "Muy Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2026-09",
   "est": "ET Nueva",
   "linea": "Línea AT",
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 2,
   "proyecto": "PE Pampa Sur",
   "tipoCliente": "DPI",
   "tecnologia": "Eólico",
   "potencia": 180,
   "tamano": "Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2026-11",
   "est": "ET Nueva",
   "linea": "Línea AT",
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 3,
   "proyecto": "BESS Norte I",
   "tipoCliente": "DPI",
   "tecnologia": "Bess",
   "potencia": 120,
   "tamano": "Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2026-10",
   "est": "Ampliación ET",
   "linea": "Línea MT",
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 0.6,
   "duracion": null
  },
  {
   "id": 4,
   "proyecto": "BESS Norte II",
   "tipoCliente": "DPI",
   "tecnologia": "Bess",
   "potencia": 80,
   "tamano": "Mediano",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2027-01",
   "est": "Ampliación ET",
   "linea": null,
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 0.6,
   "duracion": null
  },
  {
   "id": 5,
   "proyecto": "BESS Cuyo",
   "tipoCliente": "DPI",
   "tecnologia": "Bess",
   "potencia": 60,
   "tamano": "Mediano",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2027-03",
   "est": null,
   "linea": "Línea MT",
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 0.6,
   "duracion": null
  },
  {
   "id": 6,
   "proyecto": "PS Valle Fértil",
   "tipoCliente": "DPI",
   "tecnologia": "Solar",
   "potencia": 90,
   "tamano": "Mediano",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2027-02",
   "est": "ET Nueva",
   "linea": "Línea MT",
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 7,
   "proyecto": "CC Luján",
   "tipoCliente": "DPI",
   "tecnologia": "Termico",
   "potencia": 250,
   "tamano": "Grande",
   "nivelDNN": null,
   "estado": "Probable",
   "fechaInicio": "2027-05",
   "est": "Ampliación ET",
   "linea": null,
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 8,
   "proyecto": "PS Altiplano",
   "tipoCliente": "DPI",
   "tecnologia": "Solar",
   "potencia": 450,
   "tamano": "Muy Grande",
   "nivelDNN": null,
   "estado": "Probable",
   "fechaInicio": "2027-06",
   "est": "ET Nueva",
   "linea": "Línea AT",
   "simulable": true,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 9,
   "proyecto": "DNN Eólico Patagonia",
   "tipoCliente": "DNN",
   "tecnologia": "Eólico",
   "potencia": 400,
   "tamano": "Muy Grande",
   "nivelDNN": "DNN Cat2",
   "estado": "En estudio",
   "fechaInicio": "2026-10",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 10,
   "proyecto": "DNN Solar Catamarca",
   "tipoCliente": "DNN",
   "tecnologia": "Solar",
   "potencia": 200,
   "tamano": "Grande",
   "nivelDNN": "DNN Cat1",
   "estado": "En estudio",
   "fechaInicio": "2026-12",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 11,
   "proyecto": "DNN BESS Litoral",
   "tipoCliente": "DNN",
   "tecnologia": "Bess",
   "potencia": 150,
   "tamano": "Grande",
   "nivelDNN": "DNN Cat1",
   "estado": "En estudio",
   "fechaInicio": "2027-02",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 12,
   "proyecto": "DNN Solar La Rioja",
   "tipoCliente": "DNN",
   "tecnologia": "Solar",
   "potencia": 350,
   "tamano": "Muy Grande",
   "nivelDNN": "DNN Cat2",
   "estado": "En estudio",
   "fechaInicio": "2027-04",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": null,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 13,
   "proyecto": "O&M Parques Solares",
   "tipoCliente": "O&M",
   "tecnologia": "Solar",
   "potencia": 600,
   "tamano": "Muy Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2027-01",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": 2400,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 14,
   "proyecto": "O&M Parques Eólicos",
   "tipoCliente": "O&M",
   "tecnologia": "Eólico",
   "potencia": 350,
   "tamano": "Muy Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2027-01",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": 1800,
   "factorSolapamiento": 1.0,
   "duracion": null
  },
  {
   "id": 15,
   "proyecto": "O&M BESS",
   "tipoCliente": "O&M",
   "tecnologia": "Bess",
   "potencia": 200,
   "tamano": "Grande",
   "nivelDNN": null,
   "estado": "Confirmado",
   "fechaInicio": "2026-10",
   "est": null,
   "linea": null,
   "simulable": false,
   "hhParque": null,
   "hhEt": null,
   "hhLinea": null,
   "hhProy": 1200,
   "factorSolapamiento": 1.0,
   "duracion": null
  }
 ]
};
