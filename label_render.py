"""
Utilidades de formato de texto para imprimir una LabelGroup en una impresora
térmica ESC/POS. No depende de python-escpos: son funciones puras, fáciles
de probar sin hardware ni la librería instalada.
"""

from __future__ import annotations

import textwrap
from typing import Optional

from zpl_parser import LabelGroup

# Impresoras térmicas de recibo típicas: ~48 caracteres por línea en 80mm
# (fuente normal) y ~32 en 58mm. Es una aproximación -- python-escpos también
# permite achicar la fuente con set(width=..., height=...) si el texto no
# entra, pero para una etiqueta de producto (nombre corto + SKU) alcanza con
# ajustar el ancho de reflow. Para anchos que no están en esta tabla (por
# ejemplo, el ancho de una etiqueta individual en un rollo de etiquetas
# troqueladas: 50mm, 40mm, etc.) se interpola con una aproximación lineal.
CHARS_PER_LINE_BY_WIDTH_MM = {
    58: 32,
    80: 48,
}

MM_PER_CHAR_APPROX = 1.7  # ~1.7mm por carácter en fuente normal


def chars_per_line_for_width(ancho_mm: float) -> int:
    if ancho_mm in CHARS_PER_LINE_BY_WIDTH_MM:
        return CHARS_PER_LINE_BY_WIDTH_MM[ancho_mm]
    return max(8, round(ancho_mm / MM_PER_CHAR_APPROX))


# Alto aproximado que ocupa el código de barras (con el texto legible debajo)
# más una línea de texto normal, en milímetros. Sirve para estimar cuántas
# líneas de descripción entran en una etiqueta troquelada de alto fijo (ej.
# 25mm) sin invadir la etiqueta siguiente.
BARCODE_BLOCK_HEIGHT_MM = 9.0
LINE_HEIGHT_MM = 3.2


def max_lines_for_height(alto_mm: Optional[float]) -> int:
    """Estima cuántas líneas de texto entran debajo del código de barras.

    Si no se especifica el alto de la etiqueta (rollo continuo, sin
    troquelado), se asume un valor conservador de 3 líneas como hasta ahora.
    """
    if not alto_mm:
        return 3
    disponible = alto_mm - BARCODE_BLOCK_HEIGHT_MM
    return max(1, int(disponible // LINE_HEIGHT_MM))


def wrap_description(desc: str, ancho_mm: float, max_lines: int = 3) -> list[str]:
    width = chars_per_line_for_width(ancho_mm)
    lines = textwrap.wrap(desc, width=width) or [""]
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [lines[max_lines - 1][: width - 1] + "…"]
    return lines


def build_label_text_block(
    group: LabelGroup, ancho_mm: float, alto_mm: Optional[float] = None
) -> list[str]:
    """Devuelve las líneas de texto (sin el código de barras) para una etiqueta."""
    lines = wrap_description(group.description, ancho_mm, max_lines_for_height(alto_mm))
    if group.sku:
        lines.append(f"SKU: {group.sku}")
    return lines
