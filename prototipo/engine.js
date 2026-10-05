/*
 * Motor de capacidad de Ingeniería — espejo JS de backend/app/motor.py.
 * Corre en el navegador (simulación instantánea, sin ida y vuelta al servidor)
 * y en Node (para el test de paridad con Python).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CapEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const TIPOS_CLIENTE = ['DPI', 'DNN', 'O&M'];
  const MAX_MESES = 120; // tope del horizonte extendido automáticamente (10 años)
  const MESES_SENSIBILIDAD = 3; // una sensibilidad DNN arranca 3 meses después de que termina el bloque anterior

  const mesIdx = (ym) => { const [y, m] = ym.split('-').map(Number); return y * 12 + (m - 1); };
  const mesStr = (i) => `${Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}`;
  const vacio = (v) => v === null || v === undefined || v === '';

  function interpolar(puntos, x) {
    const p = puntos.slice().sort((a, b) => a[0] - b[0]);
    if (p.length === 1) return p[0][1];
    let i = 0;
    while (i < p.length - 2 && x > p[i + 1][0]) i++;
    const [x0, y0] = p[i], [x1, y1] = p[i + 1];
    return Math.max(0, y0 + (y1 - y0) * (x - x0) / (x1 - x0));
  }

  const TAMANOS = ['Chico', 'Mediano', 'Grande', 'Muy Grande'];

  // Tamaño cargado o, si falta, el que corresponde a la potencia según las tablas de HH Parque.
  function tamano(p, params) {
    if (!vacio(p.tamano)) return p.tamano;
    const mw = Number(p.potencia) || 0;
    let elegido = TAMANOS[0];
    for (const t of TAMANOS) {
      const puntos = params.parque[`${p.tecnologia}|${t}`];
      if (puntos && Math.min(...puntos.map((q) => q[0])) <= mw) elegido = t;
    }
    return elegido;
  }

  function hhParqueBase(p, params) {
    const puntos = params.parque[`${p.tecnologia}|${tamano(p, params)}`];
    return puntos ? interpolar(puntos, Number(p.potencia) || 0) : 0;
  }

  // ≙ Forecast_Componentes
  // ---- tecnología «Otro»: plan de recursos manual (especialidad × mes) ----
  const HH_PERSONA_DEFECTO = 140 * 0.85;
  const esOtro = (p) => p.tecnologia === 'Otro';
  function planHH(p, params) {
    const plan = p.planManual || {};
    const n = Math.trunc(Number(plan.meses) || 0);
    const f = (plan.unidad || 'personas') === 'personas' ? Number(params.hhPersonaMes) || HH_PERSONA_DEFECTO : 1;
    const out = {};
    for (const [esp, vals] of Object.entries(plan.valores || {})) {
      const v = (vals || []).slice(0, n).map((x) => (Number(x) || 0) * f);
      while (v.length < n) v.push(0);
      out[esp] = v;
    }
    return out;
  }
  function curvasDe(p, curvas, params) {
    if (!esOtro(p)) return curvas;
    const hh = planHH(p, params);
    let total = 0;
    for (const v of Object.values(hh)) for (const x of v) total += x;
    const c = {};
    if (total > 0) for (const [e, v] of Object.entries(hh)) c[e] = v.map((x) => x / total);
    return { Manual: c };
  }

  function componentes(p, params) {
    if (esOtro(p)) {
      let total = 0;
      for (const v of Object.values(planHH(p, params))) for (const x of v) total += x;
      return [{ componente: 'Otro', curva: 'Manual', hh: total }];
    }
    if (p.tipoCliente === 'DNN') {
      const hh = !vacio(p.hhProy) ? p.hhProy : hhParqueBase(p, params) * (params.factorDNN[p.nivelDNN] || 0);
      return [{ componente: 'DNN', curva: p.nivelDNN, hh: Number(hh) }];
    }
    if (p.tipoCliente === 'O&M') {
      const hh = !vacio(p.hhProy) ? p.hhProy : hhParqueBase(p, params) * params.factorOM;
      return [{ componente: 'O&M', curva: 'O&M', hh: Number(hh) }];
    }
    const comps = [{ componente: 'Parque', curva: p.tecnologia,
      hh: Number(!vacio(p.hhParque) ? p.hhParque : hhParqueBase(p, params)) }];
    if (!vacio(p.est)) {
      let hh;
      if (!vacio(p.hhEt)) hh = p.hhEt;
      else {
        hh = params.et[tamano(p, params)] || 0;
        if (p.est === 'Ampliación ET') hh *= params.factorAmpliacionET;
      }
      comps.push({ componente: 'ET', curva: p.est, hh: Number(hh) });
    }
    if (!vacio(p.linea)) {
      let hh;
      if (!vacio(p.hhLinea)) hh = p.hhLinea;
      else {
        hh = params.linea[tamano(p, params)] || 0;
        if (p.linea === 'Línea MT') hh *= params.factorLineaMT;
      }
      comps.push({ componente: 'Línea', curva: p.linea, hh: Number(hh) });
    }
    return comps;
  }

  function aplicarEscenario(datos, escenario) {
    escenario = escenario || {};
    const cambios = escenario.proyectos || {};
    const proyectos = datos.proyectos.map((p) => {
      const q = Object.assign({ incluir: true }, p, { desplazamiento: 0 });
      const c = cambios[String(p.id)];
      if (c) for (const k of Object.keys(c)) if (k !== 'id') q[k] = c[k];
      return q;
    });
    const base = datos.capacidad;
    const cc = escenario.capacidad || {};
    const cap = {
      hhMesPersona: 'hhMesPersona' in cc ? cc.hhMesPersona : base.hhMesPersona,
      eficiencia: 'eficiencia' in cc ? cc.eficiencia : base.eficiencia,
      dotacion: Object.assign({}, base.dotacion, cc.dotacion || {}),
      subcontratoHH: Object.assign({}, base.subcontratoHH || {}, cc.subcontratoHH || {}),
      eventos: (base.eventos || []).concat(cc.eventos || []),
      staff: 'staff' in cc ? cc.staff : (base.staff || []),
    };
    return { proyectos, cap };
  }

  const largoCurva = (curvas, nombre) =>
    Math.max(0, ...Object.values(curvas[nombre] || {}).map((v) => v.length));

  function duracionBase(p, curvas, params) {
    curvas = curvasDe(p, curvas, params);
    return Math.max(0, ...componentes(p, params).map((c) => largoCurva(curvas, c.curva)));
  }

  // Estira o comprime una curva a nNuevo meses conservando su suma y su forma.
  function reescalar(factores, nNuevo) {
    const n = factores.length;
    if (nNuevo === n || n === 0) return factores.slice();
    const acum = [0];
    for (const f of factores) acum.push(acum[acum.length - 1] + f);
    const c = (t) => {
      const i = Math.floor(t);
      if (i >= n) return acum[n];
      return acum[i] + factores[i] * (t - i);
    };
    const out = [];
    for (let j = 0; j < nNuevo; j++) out.push(c((j + 1) * n / nNuevo) - c(j * n / nNuevo));
    return out;
  }

  function largoComponente(nC, nBase, duracion) {
    if (vacio(duracion) || !nBase) return nC;
    return Math.max(1, Math.floor(nC * Math.trunc(Number(duracion)) / nBase + 0.5));
  }

  // ≙ Forecast_Mes_V4 : HH Forecast = HHComponente × Factor × Factor Solapamiento
  // Con p.duracion (meses) cada curva se reescala: mismas HH totales, otra intensidad mensual.
  const sensibilidades = (p) => (p.tipoCliente === 'DNN' ? Math.max(0, Math.trunc(Number(p.sensibilidades) || 0)) : 0);

  // [[desplazamiento, duración]] del bloque original y de cada sensibilidad DNN.
  function bloques(p, curvas, params) {
    curvas = curvasDe(p, curvas, params);
    const comps = componentes(p, params);
    const nBase = Math.max(0, ...comps.map((c) => largoCurva(curvas, c.curva)));
    const dur = Math.max(0, ...comps.map((c) => largoComponente(largoCurva(curvas, c.curva), nBase, p.duracion)));
    const paso = dur - 1 + MESES_SENSIBILIDAD;
    return Array.from({ length: sensibilidades(p) + 1 }, (_, b) => [b * paso, dur]);
  }

  function forecast(proyectos, curvas, params) {
    const filas = [];
    for (const p of proyectos) {
      if (p.incluir === false) continue;
      const inicio = mesIdx(p.fechaInicio) + (Number(p.desplazamiento) || 0);
      const solap = vacio(p.factorSolapamiento) || esOtro(p) ? 1 : Number(p.factorSolapamiento); // «Otro»: sin solapamiento
      const cv = curvasDe(p, curvas, params);
      const comps = componentes(p, params);
      const nBase = Math.max(0, ...comps.map((c) => largoCurva(cv, c.curva)));
      const desp = bloques(p, curvas, params).map((x) => x[0]);
      for (const c of comps) {
        const curva = cv[c.curva] || {};
        const nC = largoCurva(cv, c.curva);
        const nNuevo = largoComponente(nC, nBase, p.duracion);
        for (const esp of Object.keys(curva)) {
          let factores = curva[esp];
          if (nNuevo !== nC) factores = reescalar(factores.concat(new Array(nC - factores.length).fill(0)), nNuevo);
          desp.forEach((off, b) => { // b = 0 original, 1.. sensibilidades
            factores.forEach((f, k) => {
              if (f === 0) return;
              filas.push({
                proyectoId: p.id, proyecto: p.proyecto, tipoCliente: p.tipoCliente,
                componente: c.componente, bloque: b, curva: c.curva, mes: inicio + off + k, mesCurva: k + 1, especialidad: esp,
                factor: f, hhComponente: c.hh, hh: c.hh * f * solap,
              });
            });
          });
        }
      }
    }
    return filas;
  }

  const personaActiva = (s, mes) =>
    (vacio(s.desde) || mes >= mesIdx(s.desde)) && (vacio(s.hasta) || mes <= mesIdx(s.hasta));

  // Con nómina (cap.staff) cuenta las personas activas en el mes ponderadas por dedicación;
  // sin nómina usa la dotación numérica.
  function personasBase(cap, mes, esp) {
    const staff = cap.staff || [];
    if (staff.length) {
      let total = 0;
      for (const s of staff) {
        if (s.simulado === false) continue; // destildado en la nómina: sus horas no cuentan
        if (s.especialidad === esp && personaActiva(s, mes)) total += vacio(s.dedicacion) ? 1 : Number(s.dedicacion);
      }
      return total;
    }
    return cap.dotacion[esp] || 0;
  }

  function capacidadMes(cap, mes, esp) {
    let personas = personasBase(cap, mes, esp);
    for (const ev of cap.eventos || []) {
      if (ev.especialidad !== esp) continue;
      if (mes < mesIdx(ev.desde)) continue;
      if (ev.hasta && mes > mesIdx(ev.hasta)) continue;
      personas += ev.delta;
    }
    personas = Math.max(0, personas);
    return personas * cap.hhMesPersona * cap.eficiencia + ((cap.subcontratoHH || {})[esp] || 0);
  }

  const ocupacion = (d, c) => (c > 0 ? d / c : d > 0 ? Infinity : 0);

  function calcular(datos, escenario) {
    const { proyectos, cap } = aplicarEscenario(datos, escenario);
    const esps = datos.especialidades;
    const params = Object.assign({}, datos.parametros, { hhPersonaMes: cap.hhMesPersona * cap.eficiencia });
    const filas = forecast(proyectos, datos.curvas, params);
    const m0 = mesIdx(datos.horizonte.desde);
    let n = datos.horizonte.meses;
    // Si algún proyecto termina después del horizonte configurado, se extiende hasta su último mes.
    if (datos.horizonte.extender !== false && filas.length) {
      let ultimo = -Infinity;
      for (const f of filas) if (f.mes > ultimo) ultimo = f.mes;
      n = Math.max(n, Math.min(ultimo - m0 + 1, MAX_MESES));
    }
    const meses = Array.from({ length: n }, (_, i) => m0 + i);
    // Los indicadores miran hacia adelante: desde kpiDesde (p. ej. el mes actual).
    const kpi0 = datos.horizonte.kpiDesde ? mesIdx(datos.horizonte.kpiDesde) : m0;
    const pos = new Map(meses.map((m, i) => [m, i]));
    const ei = new Map(esps.map((e, i) => [e, i]));

    const dem = meses.map(() => esps.map(() => 0));
    const demTipo = meses.map(() => TIPOS_CLIENTE.map(() => 0));
    const demTipoEsp = meses.map(() => esps.map(() => TIPOS_CLIENTE.map(() => 0)));
    const porProy = new Map(), porTipo = {}, porComp = {};
    for (const f of filas) {
      porProy.set(f.proyecto, (porProy.get(f.proyecto) || 0) + f.hh);
      porTipo[f.tipoCliente] = (porTipo[f.tipoCliente] || 0) + f.hh;
      porComp[f.componente] = (porComp[f.componente] || 0) + f.hh;
      const i = pos.get(f.mes);
      if (i === undefined) continue;
      const j = ei.get(f.especialidad), t = TIPOS_CLIENTE.indexOf(f.tipoCliente);
      dem[i][j] += f.hh;
      demTipo[i][t] += f.hh;
      demTipoEsp[i][j][t] += f.hh;
    }
    const capm = meses.map((m) => esps.map((e) => capacidadMes(cap, m, e)));
    const ocup = meses.map((_, i) => esps.map((_, j) => ocupacion(dem[i][j], capm[i][j])));

    let maxOcup = { valor: 0, mes: null, especialidad: null };
    let primerCritico = null, hhExc = 0;
    const cuellos = {};
    for (const e of esps) cuellos[e] = { mesesCriticos: 0, hhExcedidas: 0, maxOcupacion: 0,
      mesPico: null, maxExceso: 0, primerMesCritico: null };
    meses.forEach((m, i) => {
      if (m < kpi0) return;
      const criticas = [];
      esps.forEach((e, j) => {
        const o = ocup[i][j], exc = Math.max(0, dem[i][j] - capm[i][j]);
        hhExc += exc;
        const cu = cuellos[e];
        cu.hhExcedidas += exc;
        cu.maxExceso = Math.max(cu.maxExceso, exc);
        if (o > cu.maxOcupacion) { cu.maxOcupacion = o; cu.mesPico = mesStr(m); }
        if (o > 1) {
          cu.mesesCriticos++;
          criticas.push(e);
          if (cu.primerMesCritico === null) cu.primerMesCritico = mesStr(m);
        }
        if (o > maxOcup.valor) maxOcup = { valor: o, mes: mesStr(m), especialidad: e };
      });
      if (criticas.length && primerCritico === null) primerCritico = { mes: mesStr(m), especialidades: criticas };
    });
    const hhPersona = cap.hhMesPersona * cap.eficiencia;
    for (const cu of Object.values(cuellos)) {
      cu.personasAdicionales = hhPersona ? Math.ceil(Math.round(cu.maxExceso / hhPersona * 1e6) / 1e6) : null;
    }

    const total = [...porProy.values()].reduce((a, b) => a + b, 0);
    let acum = 0;
    const pareto = [...porProy.entries()]
      .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
      .map(([proyecto, hh]) => {
        acum += hh;
        return { proyecto, hh, pct: total ? hh / total : 0, pctAcum: total ? acum / total : 0 };
      });

    const mixTipoCliente = {};
    for (const t of TIPOS_CLIENTE) mixTipoCliente[t] = porTipo[t] || 0;

    return {
      meses: meses.map(mesStr), kpiDesde: mesStr(Math.max(kpi0, m0)), especialidades: esps,
      demanda: dem, capacidad: capm, ocupacion: ocup,
      demandaPorTipo: demTipo, demandaPorTipoEsp: demTipoEsp,
      kpis: {
        maxOcupacion: maxOcup, primerMesCritico: primerCritico, hhExcedidas: hhExc,
        hhForecastHorizonte: dem.reduce((a, r, i) => a + (meses[i] >= kpi0 ? r.reduce((x, y) => x + y, 0) : 0), 0),
        hhForecastTotal: total,
      },
      cuellos, pareto, mixTipoCliente, mixComponente: porComp,
      proyectos, filas,
    };
  }

  function detalle(res, mes, especialidad) {
    const m = mesIdx(mes), agg = new Map();
    for (const f of res.filas) {
      if (f.mes !== m || f.especialidad !== especialidad) continue;
      const k = f.proyecto + '\u0000' + f.componente + (f.bloque ? ' · sensibilidad ' + f.bloque : '');
      agg.set(k, (agg.get(k) || 0) + f.hh);
    }
    return [...agg.entries()].map(([k, hh]) => {
      const [proyecto, componente] = k.split('\u0000');
      return { proyecto, componente, hh };
    }).sort((a, b) => b.hh - a.hh);
  }

  function mejorInicio(datos, escenario, proyectoId, desde = -3, hasta = 12) {
    const esc = JSON.parse(JSON.stringify(escenario || {}));
    esc.proyectos = esc.proyectos || {};
    const clave = String(proyectoId), base = esc.proyectos[clave] || {};
    const pruebas = [];
    for (let d = desde; d <= hasta; d++) {
      esc.proyectos[clave] = Object.assign({}, base, { desplazamiento: d });
      const k = calcular(datos, esc).kpis;
      pruebas.push({ desplazamiento: d, hhExcedidas: k.hhExcedidas, maxOcupacion: k.maxOcupacion.valor });
    }
    const r6 = (x) => Math.round(x * 1e6) / 1e6;
    const mejor = pruebas.reduce((a, b) => {
      const da = r6(a.hhExcedidas), db = r6(b.hhExcedidas);
      if (db < da) return b;
      if (db === da && Math.abs(b.desplazamiento) < Math.abs(a.desplazamiento)) return b;
      return a;
    });
    return { mejor, pruebas };
  }

  /* Personas mínimas a sumar por especialidad para que ningún mes (desde kpiDesde) supere el
     umbral (búsqueda incremental; el resultado respeta eventos y subcontratos). */
  function dotacionMinima(datos, escenario, umbral = 1) {
    const esc = JSON.parse(JSON.stringify(escenario || {}));
    esc.capacidad = esc.capacidad || {};
    // Suma personas como altas desde el inicio del horizonte: sirve con dotación y con nómina.
    const evBase = esc.capacidad.eventos || [];
    const res = {};
    for (let j = 0; j < datos.especialidades.length; j++) {
      const e = datos.especialidades[j];
      let extra = 0;
      for (; extra <= 50; extra++) {
        esc.capacidad.eventos = extra ? evBase.concat([{ especialidad: e, desde: datos.horizonte.desde, hasta: null, delta: extra }]) : evBase;
        const r = calcular(datos, esc);
        const i0 = Math.max(0, mesIdx(r.kpiDesde) - mesIdx(r.meses[0]));
        if (r.ocupacion.every((fila, i) => i < i0 || fila[j] <= umbral)) break;
      }
      res[e] = extra;
    }
    return res;
  }

  return { TIPOS_CLIENTE, TAMANOS, tamano, mesIdx, mesStr, interpolar, componentes, aplicarEscenario, forecast,
    esOtro, planHH, curvasDe, HH_PERSONA_DEFECTO, personasBase, personaActiva, sensibilidades, bloques, MESES_SENSIBILIDAD, largoCurva, duracionBase, reescalar, largoComponente,
    capacidadMes, calcular, detalle, mejorInicio, dotacionMinima };
});
