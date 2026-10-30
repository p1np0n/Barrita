"""Genera el catálogo mayorista de Over Power Armor (OPA) a partir de los
precios públicos de Shopify.

El margen de la tienda se calcula sobre el precio de venta sugerido (PVP):
    precio mayorista = PVP × (1 − margen)
Así, una tienda que compra al nivel Oro (30 %) y vende al PVP se queda con el
30 % del precio de venta. Todos los precios en CLP con IVA incluido.
"""
import csv
import json
from pathlib import Path

AQUI = Path(__file__).parent
NIVELES = [("Bronce", 0.20, 60000), ("Plata", 0.25, 150000), ("Oro", 0.30, 300000)]


def redondear(valor, paso=10):
    return int(round(valor / paso) * paso)


def main():
    productos = json.loads((AQUI / "productos_shopify.json").read_text(encoding="utf-8"))
    filas = []
    # Los packs (dados y kit de inicio) son exclusivos de la tienda web.
    for p in (p for p in productos if not p.get("exclusivo_web")):
        fila = {
            "Producto": p["producto"],
            "Categoría": p["tipo"],
            "Variantes": p["variantes"],
            "Stock (u.)": p["stock"],
            "Peso (kg)": "" if p["peso_kg"] is None else p["peso_kg"],
            "PVP sugerido": p["pvp"],
        }
        for nombre, margen, _ in NIVELES:
            mayorista = redondear(p["pvp"] * (1 - margen))
            fila[f"Precio {nombre} ({int(margen * 100)} %)"] = mayorista
            if p["costo"]:
                # Margen que le queda a OPA vendiendo a ese precio.
                fila[f"Margen OPA {nombre}"] = f"{(mayorista - p['costo']) / mayorista:.0%}"
                if mayorista <= p["costo"]:
                    raise SystemExit(f"{p['producto']}: precio {nombre} bajo el costo")
            else:
                fila[f"Margen OPA {nombre}"] = "sin costo cargado"
        filas.append(fila)

    salida = AQUI / "catalogo_mayorista.csv"
    with salida.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), delimiter=";")
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} productos → {salida.name}")
    for nombre, margen, minimo in NIVELES:
        minimo_clp = f"{minimo:,}".replace(",", ".")
        print(f"  {nombre}: tienda gana {margen:.0%} del PVP, pedido mínimo ${minimo_clp}")


if __name__ == "__main__":
    main()
