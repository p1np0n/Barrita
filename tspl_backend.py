"""
Generación de comandos TSPL (TSC Printer Language) para imprimir etiquetas.

Muchas impresoras térmicas de etiquetas chinas "genéricas" (las que vienen
con sensor de separación/gap entre etiquetas troqueladas, y traen su propio
programa tipo "Label" para diseñar etiquetas) NO hablan ESC/POS -- hablan
TSPL, el lenguaje de comandos de TSC que un montón de clones adoptaron como
estándar de facto. Si una impresora no imprime nada con el backend ESC/POS
pero sí imprime desde su programa de diseño de etiquetas propio, es casi
seguro que es una de estas.

Este módulo no depende de python-escpos: arma directamente los bytes TSPL
como texto plano. Se mandan con el mismo transporte de conexión (Win32Raw /
Usb / File) escribiéndolos con el método `_raw()` de esos objetos, sin pasar
por ninguna de las funciones de formato ESC/POS de esa librería (que no
tienen nada que ver acá).
"""

from __future__ import annotations

import textwrap
from typing import Optional

from zpl_parser import LabelGroup

# TSPL trabaja en puntos (dots), no en mm -- hay que convertir según el DPI
# real de la impresora. La gran mayoría de estas impresoras chinas de
# etiquetas son de 203dpi; algunas más nuevas/caras son 300dpi.
DEFAULT_DPI = 203

# Fuente interna TSPL más chica (~8x12 dots a 1x) -- la más conveniente para
# etiquetas chicas donde hay que aprovechar cada milímetro.
FONT = "1"
FONT_WIDTH_DOTS = 8
FONT_HEIGHT_DOTS = 12
LINE_SPACING_DOTS = 4  # espacio extra entre líneas de texto

MARGIN_MM = 2.0
BARCODE_HEIGHT_MM = 8.0
BARCODE_TO_TEXT_GAP_MM = 3.0
BARCODE_MODULE_DOTS = 2  # el "narrow/wide" que mandamos en el comando BARCODE


def mm_to_dots(mm: float, dpi: int) -> int:
    return round(mm * dpi / 25.4)


def _sanitize(text: str) -> str:
    """Evita que comillas en el texto rompan el comando TSPL (que usa "...")."""
    return text.replace('"', "'")


def _chars_per_line(ancho_mm: float, dpi: int) -> int:
    ancho_dots = mm_to_dots(ancho_mm, dpi) - 2 * mm_to_dots(MARGIN_MM, dpi)
    return max(6, ancho_dots // FONT_WIDTH_DOTS)


def max_lines_for_height(alto_mm: float, dpi: int) -> int:
    alto_dots = mm_to_dots(alto_mm, dpi)
    barcode_dots = mm_to_dots(BARCODE_HEIGHT_MM + BARCODE_TO_TEXT_GAP_MM, dpi)
    margin_dots = mm_to_dots(MARGIN_MM, dpi)
    disponible = alto_dots - barcode_dots - margin_dots
    line_h = FONT_HEIGHT_DOTS + LINE_SPACING_DOTS
    return max(1, disponible // line_h)


def _code128_width_dots(content: str, module_dots: int = BARCODE_MODULE_DOTS) -> int:
    """Estima el ancho en puntos de un código CODE128, asumiendo Code Set B
    (1 módulo de 11 unidades por carácter, que es el caso típico para
    códigos alfanuméricos como los que usa ML). No es exacto al 100% --
    Code128 a veces cambia de code-set internamente para ahorrar espacio en
    tramos puramente numéricos -- pero alcanza para centrar razonablemente
    bien sin tener que implementar el algoritmo de codificación completo.

    Fórmula: inicio (11 módulos) + 1 módulo de 11 por cada carácter de datos
    + checksum (11 módulos) + parada (13 módulos).
    """
    n = max(1, len(content))
    modules = 11 * (n + 2) + 13
    return modules * module_dots


def _wrap(text: str, ancho_mm: float, dpi: int, max_lines: int) -> list[str]:
    width = _chars_per_line(ancho_mm, dpi)
    lines = textwrap.wrap(text, width=width) or [""]
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [lines[max_lines - 1][: width - 1] + "…"]
    return lines


def _header_lines(ancho_mm: float, alto_mm: float, gap_mm: float) -> list[str]:
    return [
        "CODEPAGE 1252",
        f"SIZE {ancho_mm:g} mm,{alto_mm:g} mm",
        f"GAP {gap_mm:g} mm,0 mm",
        "DIRECTION 1",
        "REFERENCE 0,0",
        "SET PEEL OFF",
        "SET CUTTER OFF",
    ]


def _draw_label(
    lines: list[str],
    x0_dots: int,
    ancho_mm: float,
    alto_mm: float,
    dpi: int,
    code: str,
    text_lines: list[str],
    center_h: bool = True,
    center_v: bool = True,
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
) -> None:
    """Agrega los comandos BARCODE/TEXT de una etiqueta individual, offseteados
    en x0_dots puntos desde el borde izquierdo de la fila (para soportar
    varias columnas en el mismo ancho de papel).

    `center_h`/`center_v` centran el bloque código+texto dentro del área útil
    de la etiqueta (ancho/alto menos los márgenes). `offset_x_mm`/`offset_y_mm`
    permiten un ajuste fino en milímetros por encima del centrado (o de la
    posición contra el margen, si el centrado está desactivado), para
    corregir a mano si el cálculo automático no queda perfecto.
    """
    margin_dots = mm_to_dots(MARGIN_MM, dpi)
    ancho_dots = mm_to_dots(ancho_mm, dpi)
    alto_dots = mm_to_dots(alto_mm, dpi)
    available_w = max(0, ancho_dots - 2 * margin_dots)
    available_h = max(0, alto_dots - 2 * margin_dots)

    barcode_height_dots = mm_to_dots(BARCODE_HEIGHT_MM, dpi)
    gap_dots = mm_to_dots(BARCODE_TO_TEXT_GAP_MM, dpi)
    line_h = FONT_HEIGHT_DOTS + LINE_SPACING_DOTS

    offset_x = mm_to_dots(offset_x_mm, dpi)
    offset_y = mm_to_dots(offset_y_mm, dpi)

    if center_v:
        content_h = barcode_height_dots + gap_dots + len(text_lines) * line_h
        start_y = margin_dots + max(0, (available_h - content_h) // 2)
    else:
        start_y = margin_dots
    barcode_y = start_y + offset_y
    text_y_start = barcode_y + barcode_height_dots + gap_dots

    if center_h:
        barcode_w = _code128_width_dots(code)
        barcode_x = x0_dots + margin_dots + max(0, (available_w - barcode_w) // 2)
    else:
        barcode_x = x0_dots + margin_dots
    barcode_x += offset_x

    # A diferencia de ESC/POS, TSPL no necesita un prefijo de "code set" para
    # CODE128 -- el firmware elige la codificación internamente.
    lines.append(
        f'BARCODE {barcode_x},{barcode_y},"128",{barcode_height_dots},1,0,2,2,"{_sanitize(code)}"'
    )
    y = text_y_start
    for line in text_lines:
        if center_h:
            line_w = len(line) * FONT_WIDTH_DOTS
            text_x = x0_dots + margin_dots + max(0, (available_w - line_w) // 2) + offset_x
        else:
            text_x = x0_dots + margin_dots + offset_x
        lines.append(f'TEXT {text_x},{y},"{FONT}",0,1,1,"{_sanitize(line)}"')
        y += line_h


def build_tspl_batch(
    groups: list[LabelGroup],
    ancho_mm: float,
    alto_mm: float,
    gap_mm: float = 2.0,
    dpi: int = DEFAULT_DPI,
    columns: int = 1,
    col_gap_mm: float = 0.0,
    center_h: bool = True,
    center_v: bool = True,
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
) -> bytes:
    """Arma el trabajo TSPL completo (todas las etiquetas) en un solo buffer.

    `columns` es la cantidad de etiquetas que hay una al lado de la otra en
    el mismo ancho de papel (ej. 2, en un rollo de etiquetas de 50mm de
    ancho pegadas de a pares). `ancho_mm`/`alto_mm` siguen siendo el tamaño
    de UNA etiqueta individual, no el ancho total del rollo -- el ancho
    total para el comando SIZE se calcula solo a partir de columns.
    """
    total_ancho_mm = ancho_mm * columns + col_gap_mm * max(0, columns - 1)
    lines: list[str] = _header_lines(total_ancho_mm, alto_mm, gap_mm)

    max_lines = max_lines_for_height(alto_mm, dpi)
    col_stride_dots = mm_to_dots(ancho_mm + col_gap_mm, dpi)

    # Aplanamos a una secuencia de etiquetas físicas individuales, y las
    # empaquetamos de a `columns` por fila (misma lógica que usa Mercado
    # Libre para las 2 columnas de su propio ZPL).
    flat: list[LabelGroup] = []
    for g in groups:
        flat.extend([g] * max(0, g.quantity))

    for row_start in range(0, len(flat), columns):
        row = flat[row_start : row_start + columns]
        lines.append("CLS")
        for i, g in enumerate(row):
            text_lines = _wrap(g.description, ancho_mm, dpi, max_lines)
            if g.sku:
                text_lines.append(f"SKU: {g.sku}")
            _draw_label(
                lines,
                i * col_stride_dots,
                ancho_mm,
                alto_mm,
                dpi,
                g.code,
                text_lines,
                center_h=center_h,
                center_v=center_v,
                offset_x_mm=offset_x_mm,
                offset_y_mm=offset_y_mm,
            )
        lines.append("PRINT 1,1")

    payload = "\r\n".join(lines) + "\r\n"
    return payload.encode("cp1252", errors="replace")


def build_tspl_test_label(
    ancho_mm: float,
    alto_mm: float,
    gap_mm: float = 2.0,
    dpi: int = DEFAULT_DPI,
    columns: int = 1,
    col_gap_mm: float = 0.0,
    center_h: bool = True,
    center_v: bool = True,
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
) -> bytes:
    """Etiqueta de prueba con código de barras real en TSPL, con una marca
    por columna para poder verificar alineación y centrado antes de gastar
    el lote completo."""
    total_ancho_mm = ancho_mm * columns + col_gap_mm * max(0, columns - 1)
    col_stride_dots = mm_to_dots(ancho_mm + col_gap_mm, dpi)

    lines = _header_lines(total_ancho_mm, alto_mm, gap_mm) + ["CLS"]
    for i in range(columns):
        text_lines = [f"PRUEBA COL {i + 1}", f"{ancho_mm:g}x{alto_mm:g}mm {dpi}dpi"]
        _draw_label(
            lines,
            i * col_stride_dots,
            ancho_mm,
            alto_mm,
            dpi,
            "123456789",
            text_lines,
            center_h=center_h,
            center_v=center_v,
            offset_x_mm=offset_x_mm,
            offset_y_mm=offset_y_mm,
        )
    lines.append("PRINT 1,1")

    payload = "\r\n".join(lines) + "\r\n"
    return payload.encode("cp1252", errors="replace")
