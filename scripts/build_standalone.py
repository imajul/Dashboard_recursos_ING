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


if __name__ == "__main__":
    main()
