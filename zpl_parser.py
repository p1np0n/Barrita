"""
Parser de archivos ZPL exportados por Mercado Libre (etiquetas de productos).

No interpretamos el ZPL en general (eso requeriría un motor de renderizado
como Zebra Zebra Browser Print / Labelary). En su lugar, extraemos los datos
"de negocio" de cada etiqueta -- código de barras, descripción del producto y
SKU -- a partir de los campos ^FD que Mercado Libre siempre genera con la
misma estructura. Con esos datos reconstruimos una etiqueta simple e
imprimible en cualquier impresora térmica ESC/POS (no-Zebra).

Estructura típica de una "columna" de etiqueta dentro del ZPL:

    ^FO30,15^BY2,,0^BCN,54,N,N^FD<codigo>^FS       -> código de barras (Code128)
    ^FO105,75^A0N,20,25^FH^FD<codigo>^FS            -> texto legible (se repite 2 veces, efecto negrita)
    ^FO105,76^A0N,20,25^FH^FD<codigo>^FS
    ^FO16,115^A0N,18,18^FB300,2,2,L^FH^FD<desc>^FS  -> descripción del producto
    ^FO16,153^A0N,18,18^FB300,1,0,L^FH^FD^FS        -> línea reservada (casi siempre vacía)
    ^FO15,153^A0N,18,18^FB300,1,0,L^FH^FD^FS        -> misma línea, offset de negrita
    ^FO16,172^A0N,18,18^FH^FD<sku>^FS               -> "SKU: xxxxx" (o vacío)

Cada bloque ^XA...^XZ contiene DOS columnas idénticas (izquierda ~x=16-105,
derecha ~x=345-425): Mercado Libre imprime 2 etiquetas físicas por pasada.
Cada columna es una etiqueta física a imprimir, así que las contamos todas
(no las deduplicamos) para preservar la cantidad real de stickers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from collections import OrderedDict

# Patrón de una "columna" de etiqueta completa, en el orden fijo en que
# Mercado Libre siempre las genera.
_LABEL_UNIT_RE = re.compile(
    r"""
    \^BCN,54,N,N\^FD(?P<code>[^\^]*)\^FS .*?
    \^FB300,2,2,L\^FH\^FD(?P<desc>[^\^]*)\^FS .*?
    \^FO\d+,172\^A0N,18,18\^FH\^FD(?P<sku>.*?)\^FS
    """,
    re.VERBOSE | re.DOTALL,
)

_HEX_ESCAPE_RE = re.compile(r"_[0-9A-Fa-f]{2}")


def decode_zpl_hex_field(raw: str) -> str:
    """Decodifica el escapado hexadecimal que usa ^FH (indicador '_' + 2 hex).

    Mercado Libre genera las etiquetas con ^CI28 (UTF-8) y ^FH, así que
    caracteres como 'ñ' o 'í' llegan como '_C3_B1' / '_C3_AD' (los bytes UTF-8
    en hexadecimal). Reconstruimos los bytes crudos y los decodificamos como
    UTF-8 al final, para no romper secuencias multi-byte.
    """
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == "_" and i + 2 < n and re.match(r"[0-9A-Fa-f]{2}", raw[i + 1 : i + 3]):
            out.append(int(raw[i + 1 : i + 3], 16))
            i += 3
        else:
            out.extend(raw[i].encode("utf-8"))
            i += 1
    return out.decode("utf-8", errors="replace").strip()


@dataclass
class ProductLabel:
    code: str          # valor del código de barras (Code128)
    description: str
    sku: str

    def key(self):
        return (self.code, self.description, self.sku)


@dataclass
class LabelGroup:
    """Un grupo de etiquetas idénticas, con la cantidad de copias a imprimir."""

    code: str
    description: str
    sku: str
    quantity: int = 0


def parse_zpl_file(path: str) -> list[ProductLabel]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return parse_zpl_text(content)


def parse_zpl_text(content: str) -> list[ProductLabel]:
    labels: list[ProductLabel] = []
    for m in _LABEL_UNIT_RE.finditer(content):
        code = decode_zpl_hex_field(m.group("code"))
        desc = decode_zpl_hex_field(m.group("desc"))
        sku_raw = decode_zpl_hex_field(m.group("sku"))
        sku = re.sub(r"^SKU:\s*", "", sku_raw).strip()
        labels.append(ProductLabel(code=code, description=desc, sku=sku))
    return labels


def group_labels(labels: list[ProductLabel]) -> list[LabelGroup]:
    """Agrupa etiquetas idénticas y cuenta cuántas copias hay que imprimir."""
    groups: "OrderedDict[tuple, LabelGroup]" = OrderedDict()
    for lbl in labels:
        k = lbl.key()
        if k not in groups:
            groups[k] = LabelGroup(code=lbl.code, description=lbl.description, sku=lbl.sku, quantity=0)
        groups[k].quantity += 1
    return list(groups.values())


if __name__ == "__main__":
    import sys

    path = sys.argv[1]
    labels = parse_zpl_file(path)
    groups = group_labels(labels)
    print(f"Etiquetas físicas encontradas: {len(labels)}")
    print(f"Productos distintos: {len(groups)}\n")
    for g in groups:
        print(f"  x{g.quantity:>3}  código={g.code!r:20}  sku={g.sku!r:20}  {g.description}")
