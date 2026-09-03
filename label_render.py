"""
Utilidades de formato de texto para imprimir una LabelGroup en una impresora
térmica ESC/POS. No depende de python-escpos: son funciones puras, fáciles
de probar sin hardware ni la librería instalada.
"""

from __future__ import annotations

import textwrap

from zpl_parser import LabelGroup

# Impresoras térmicas de recibo típicas: ~48 caracteres por línea en 80mm
# (fuente normal) y ~32 en 58mm. Es una aproximación -- python-escpos también
# permite achicar la fuente con set(width=..., height=...) si el texto no
# entra, pero para una etiqueta de producto (nombre corto + SKU) alcanza con
# ajustar el ancho de reflow.
CHARS_PER_LINE_BY_WIDTH_MM = {
    58: 32,
    80: 48,
}


def chars_per_line_for_width(ancho_mm: int) -> int:
    return CHARS_PER_LINE_BY_WIDTH_MM.get(ancho_mm, 42)


def wrap_description(desc: str, ancho_mm: int, max_lines: int = 3) -> list[str]:
    width = chars_per_line_for_width(ancho_mm)
    lines = textwrap.wrap(desc, width=width) or [""]
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [lines[max_lines - 1][: width - 1] + "…"]
    return lines


def build_label_text_block(group: LabelGroup, ancho_mm: int) -> list[str]:
    """Devuelve las líneas de texto (sin el código de barras) para una etiqueta."""
    lines = wrap_description(group.description, ancho_mm)
    if group.sku:
        lines.append(f"SKU: {group.sku}")
    return lines
