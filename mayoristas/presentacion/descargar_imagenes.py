"""Descarga las fotos de los productos desde Shopify a presentacion/img/.

Requiere acceso a cdn.shopify.com. Si una foto no se puede bajar, el catálogo
muestra un recuadro con la categoría en su lugar.
"""
import json
import re
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
IMG = AQUI / "img"


def archivo(producto):
    return re.sub(r"[^a-z0-9]+", "-", producto.lower()).strip("-")


def main():
    IMG.mkdir(exist_ok=True)
    productos = json.loads((AQUI.parent / "productos_shopify.json").read_text(encoding="utf-8"))
    ok = 0
    for p in productos:
        ext = Path(p["imagen"].split("?")[0]).suffix or ".jpg"
        destino = IMG / (archivo(p["producto"]) + ext)
        if destino.exists():
            ok += 1
            continue
        # width=600 pide a Shopify una versión liviana de la foto.
        url = p["imagen"] + ("&" if "?" in p["imagen"] else "?") + "width=600"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                destino.write_bytes(r.read())
            ok += 1
        except OSError as e:
            print(f"sin foto: {p['producto']} ({e})")
    print(f"{ok}/{len(productos)} fotos en {IMG}")


if __name__ == "__main__":
    main()
