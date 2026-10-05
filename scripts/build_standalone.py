"""Genera dist/capacidad-ingenieria.html: la herramienta en UN solo archivo.

Incluye el motor (engine.js) y los datos (data.js) dentro del HTML, así se puede
mandar por mail/Teams o subir a SharePoint y abrir con doble clic, sin servidor
ni cuenta. Solo usa internet (opcional) para las fuentes y el reporte PDF.

Uso:  python scripts/build_standalone.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROTO = RAIZ / "prototipo"
SALIDA = RAIZ / "dist" / "capacidad-ingenieria.html"


LEEME = """CAPACIDAD DE INGENIERÍA - cómo usar la herramienta compartida
(versión del {fecha})

QUÉ HAY EN ESTA CARPETA
  capacidad-ingenieria.html  La herramienta. Se abre con doble clic.
  plan-capacidad.json        El plan vigente (lo crea y actualiza la herramienta).
  escenarios\\               Simulaciones guardadas por el equipo.
  historial\\                Una copia de cada versión guardada del plan.

Esta carpeta se sincroniza con SharePoint mediante OneDrive: todo lo que se
guarda acá lo ve el resto del equipo en segundos. No hace falta cuenta en
Claude ni en GitHub.

PRIMERA VEZ (cada usuario, una sola vez)
  1. En el Explorador de Windows, clic derecho en esta carpeta >
     "Mantener siempre en este dispositivo" (evita archivos solo en la nube).
  2. Abrir capacidad-ingenieria.html con Microsoft Edge o Google Chrome
     (Firefox no permite trabajar con carpetas).
  3. Clic en el botón "Sin carpeta compartida" (arriba, junto al título),
     escribir tu nombre y "Elegir carpeta": seleccionar ESTA carpeta y
     aceptar el permiso para ver y editar archivos.
  4. Si la carpeta no tiene plan todavía, "Guardar" lo crea.

USO DIARIO
  - Abrir el HTML desde esta carpeta. Si el navegador lo pide, aceptar el
    permiso en la barra amarilla ("Permitir y cargar el plan").
  - Hacer cambios: mover proyectos, cambiar duraciones, recursos o
    parámetros, importar la lista de proyectos (CSV de SharePoint).
  - GUARDAR (botón Guardar o Ctrl+S). Cada guardado crea una revisión
    nueva firmada con tu nombre y una copia en "historial".
  - Si otra persona guardó mientras trabajabas, la herramienta avisa y
    ofrece guardar tus cambios como escenario para no perder nada.
  - Si no tenés cambios sin guardar, los cambios de los demás se cargan
    solos (la herramienta revisa la carpeta cada 20 segundos).

LA HERRAMIENTA ES LA BASE DE DATOS DE PROYECTOS
  Todas las altas, bajas y modificaciones de proyectos se hacen acá y se
  confirman con Guardar.
  - Botón "Proyectos": tabla con todos los proyectos (código, nombre, tipo,
    nivel DNN, tecnología, MW, tamaño, POE, ET, línea, inicio, duración,
    solapamiento, estado, calendario fijo, % avance, incluir). Se edita
    directo en la celda; "+ Proyecto" agrega y la X elimina. Las filas con
    "!" tienen datos a revisar (código repetido, sin fecha, DNN sin nivel...).
  - Clic en un proyecto del Gantt: panel con todos sus datos.
  - "Importar" un CSV REEMPLAZA toda la lista: queda solo para cargas
    iniciales. Antes de aplicar muestra qué se agrega, cambia y borra.
  - "Exportar > Lista de proyectos (CSV)" genera la planilla en el formato
    de la lista DIM_Proyecto (se puede volver a importar).

STAFF DE INGENIERÍA (RECURSOS)
  Botón "Recursos" > "Staff de Ingeniería": lista con nombre, especialidad,
  % de dedicación, ingreso y egreso (opcionales) y nota.
  - La cantidad de personas de cada especialidad, mes a mes, sale de esta
    lista: cuenta a quienes están activos ese mes según su dedicación
    (50 % = media persona). Así se reflejan ingresos, egresos y licencias.
  - Columna "Simulado": tildado = sus horas suman a la capacidad;
    destildado = la persona queda en la lista pero no suma (útil para probar
    "qué pasa si no está"). El casillero del encabezado tilda o destilda a
    todos los de la especialidad filtrada.
  - "Pegar desde Excel": copiar columnas Nombre, Especialidad, Dedicación %,
    Ingreso, Egreso (y opcionalmente Simulado Si/No) y pegarlas. "Crear lista desde la dotación" arma filas
    para completar los nombres.
  - "Nivelar" agrega vacantes con nombre ("Vacante Eléctricos 1") que se
    pueden renombrar cuando se cubran.
  - Las altas y bajas del panel de cada especialidad quedan para refuerzos
    hipotéticos; las personas reales van en la lista.
  - Mientras la lista esté vacía se usa la cantidad numérica por especialidad.

HH CARGADAS A MANO
  Si la base de datos de HH no aplica a un proyecto puntual: clic en el
  proyecto > "HH del proyecto · por componente". Para cada componente
  (Parque, ET, Línea; o el total en DNN y O&M) se ve el valor del modelo y
  se puede escribir el que corresponde. Completar el "Motivo del ajuste".
  Vacío = vuelve al modelo. El proyecto queda marcado con un lápiz.
  También desde la tabla "Proyectos": columna "HH asignadas" (en gris el
  valor del modelo) y "Motivo HH". En DPI el total se reparte entre Parque,
  ET y Línea en la misma proporción; "HH netas" muestra el valor después del
  factor de solapamiento.

SENSIBILIDADES (PROYECTOS DNN)
  Clic en un proyecto DNN > "Sensibilidades" > "Agregar sensibilidad": suma
  un bloque de trabajo igual al original (mismas HH, curva y duración) que
  arranca 3 meses después de que termina el bloque anterior. Se pueden
  agregar varias y "Quitar la última". En el Gantt se ven rayadas (S1, S2...)
  y se mueven junto con el bloque original. También desde la tabla
  "Proyectos", columna "Sensib. DNN".

REGISTRO DE CAMBIOS
  Cada Guardar anota qué cambió y quién lo hizo (por ejemplo "PABRA: Inicio
  ene-27 -> jun-27"). Se ve en el diálogo de la carpeta > Historial, y en el
  aviso que aparece cuando otro usuario guardó mientras trabajabas.

SIMULAR SIN TOCAR EL PLAN VIGENTE
  Hacer los cambios y, en lugar de Guardar, usar "Escenarios > Guardar
  actual". El escenario queda en la carpeta escenarios\\ para todos y el
  plan vigente no cambia. Para descartar tus cambios: "Recargar el plan
  vigente" en el diálogo de la carpeta.

VOLVER A UNA VERSIÓN ANTERIOR
  Diálogo de la carpeta > Historial > Abrir. Revisar y presionar Guardar
  para que vuelva a ser el plan vigente.

SI APARECE "COPIAS EN CONFLICTO"
  OneDrive crea archivos como plan-capacidad-NOMBREPC.json cuando dos
  personas guardaron casi a la vez. Abrirlos desde el diálogo de la carpeta,
  pasar lo que falte al plan vigente, guardar y borrar la copia.

ACTUALIZAR LA HERRAMIENTA
  Reemplazar capacidad-ingenieria.html por la versión nueva. El plan, los
  escenarios y el historial no se tocan.
"""


def inline(nombre: str) -> str:
    codigo = (PROTO / nombre).read_text(encoding="utf-8").replace("</script", "<\\/script")
    return f"<script>/* {nombre} */\n{codigo}\n</script>"


def main() -> None:
    html = (PROTO / "index.html").read_text(encoding="utf-8")
    for nombre in ("data.js", "engine.js"):
        etiqueta = f'<script src="{nombre}"></script>'
        assert etiqueta in html, f"No se encontró {etiqueta} en index.html"
        html = html.replace(etiqueta, inline(nombre), 1)
    html = html.replace("<head>", f"<head>\n<!-- Versión autocontenida generada el {date.today():%d/%m/%Y} -->", 1)
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(html, encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)} ({SALIDA.stat().st_size / 1024:.0f} KB)")
    leeme = SALIDA.parent / "LEEME.txt"
    leeme.write_text(LEEME.replace("{fecha}", f"{date.today():%d/%m/%Y}"), encoding="utf-8-sig")
    print(f"Escrito {leeme.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
