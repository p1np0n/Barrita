"""Genera catalogo_mayorista.html; luego `node a_pdf.js` lo convierte a PDF."""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PRODUCTOS = json.loads((AQUI.parent / "productos_shopify.json").read_text(encoding="utf-8"))
ESTRELLA = [
    ("Protectores Penny Sleeves - Fit 65x90 (100 u.)", "El más vendido. Pokémon, Magic y One Piece."),
    ("Protectores Penny Sleeves - Perfect Fit 64x89 (100 u.)", "Ajuste interior para doble enfundado."),
    ("Protector Over Sleeve Rugosos 69x94", "Exterior mate rugoso, ideal para torneos."),
    ("25 Toploaders 35PT", "Rígidos, libres de ácido y PVC."),
    ("Playmate Impermeable Ecocuero", "Negro, púrpura y rojo. Base antideslizante."),
    ("Deck Box - Porta Mazo 80+", "Rotación rápida en mesón, precio de impulso."),
    ("Grading Case Nuevo Vacío", "Para exhibir cartas de valor."),
    ("Acrílico Magnético - Magnetic Holder 35pt", "Protección premium con cierre magnético."),
]
NIVELES = [("Bronce", 0.20, 60000), ("Plata", 0.25, 150000), ("Oro", 0.30, 300000)]


def clp(n):
    return "$" + f"{round(n):,}".replace(",", ".")


def r10(n):
    return int(round(n / 10) * 10)


def precio(p, m):
    return clp(r10(p["pvp"] * (1 - m)))


def fila(p, nota=""):
    celdas = "".join(f"<td class=n>{precio(p, m)}</td>" for _, m, _ in NIVELES)
    sub = f"<div class=sub>{nota}</div>" if nota else ""
    return f"<tr><td><b>{p['producto']}</b>{sub}</td><td class=n>{clp(p['pvp'])}</td>{celdas}</tr>"


por_nombre = {p["producto"]: p for p in PRODUCTOS}
estrellas = "".join(fila(por_nombre[n], nota) for n, nota in ESTRELLA)
resto = "".join(fila(p, p["variantes"]) for p in PRODUCTOS if p["producto"] not in dict(ESTRELLA) and p["stock"] > 0)
niveles = "".join(
    f"<div class=tier><span>{n}</span><b>{int(m*100)} %</b><small>margen para tu tienda<br>pedido desde {clp(mn)}</small></div>"
    for n, m, mn in NIVELES)
cab = "<tr><th>Producto</th><th class=n>Precio público</th>" + "".join(
    f"<th class=n>{n} ({int(m*100)} %)</th>" for n, m, _ in NIVELES) + "</tr>"

html = f"""<!doctype html><html lang=es><meta charset=utf-8><style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font: 10.5pt/1.45 'Helvetica Neue', Arial, sans-serif; color:#18202b; }}
h1 {{ font-size: 30pt; margin: 0; letter-spacing: -.01em; }}
h1 span {{ color:#b07a12; }}
h2 {{ font-size: 14pt; margin: 18px 0 8px; border-bottom: 2px solid #b07a12; padding-bottom: 4px; }}
.band {{ background:#1c2633; color:#eef1f5; padding: 18px 20px; border-radius: 6px; }}
.band p {{ margin: 6px 0 0; color:#c9d2dd; max-width: 150mm; }}
.tiers {{ display:flex; gap:10px; margin-top: 12px; }}
.tier {{ flex:1; border:1px solid #dde1e7; border-radius:6px; padding:10px 12px; }}
.tier span {{ font-weight:700; text-transform:uppercase; font-size:9pt; letter-spacing:.08em; color:#5b6575; }}
.tier b {{ display:block; font-size:24pt; color:#b07a12; }}
.tier small {{ color:#5b6575; }}
table {{ width:100%; border-collapse:collapse; font-size:9.5pt; }}
th, td {{ padding:6px 6px; border-bottom:1px solid #dde1e7; text-align:left; vertical-align:top; }}
th {{ font-size:8pt; text-transform:uppercase; letter-spacing:.05em; color:#5b6575; }}
.n {{ text-align:right; white-space:nowrap; }}
.sub {{ color:#5b6575; font-size:8.5pt; }}
ul {{ margin: 6px 0; padding-left: 18px; }}
.foot {{ margin-top: 14px; font-size: 9pt; color:#5b6575; }}
.pb {{ page-break-before: always; }}
</style>
<div class=band><h1>Over Power Armor <span>· Mayoristas</span></h1>
<p>Accesorios para cartas coleccionables (Pokémon, One Piece, Magic, Yu-Gi-Oh! y más), con despacho desde Maipú a todo Chile. Precios para tiendas con 20 % a 30 % de margen, vendiendo a nuestro precio público sugerido.</p></div>
<h2>Niveles para tiendas</h2>
<div class=tiers>{niveles}</div>
<ul>
<li>El margen se calcula sobre el precio público: tu tienda compra al precio del nivel y vende al precio sugerido.</li>
<li>El monto mínimo se mide a precio público. Precios en pesos chilenos con IVA incluido.</li>
<li>Compras en overpowerarmor.cl con tu cuenta de empresa y el código del nivel, o por transferencia.</li>
</ul>
<h2>Productos estrella</h2>
<table>{cab}{estrellas}</table>
<div class="pb"></div>
<h2>Resto del catálogo con stock</h2>
<table>{cab}{resto}</table>
<p class=foot>Over Power Armor · overpowerarmor.cl · irsolucioneschile@gmail.com · Maipú, Santiago. Precios vigentes al 29-10-2026, sujetos a stock.</p>
</html>"""

(AQUI / "catalogo_mayorista.html").write_text(html, encoding="utf-8")
print("catalogo_mayorista.html listo")
