"""Genera catalogo_mayorista.html; luego `node a_pdf.js` lo convierte a PDF.

Las fotos salen de presentacion/img/ (ver descargar_imagenes.py). Los packs
marcados como exclusivo_web en productos_shopify.json no se incluyen.
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

from descargar_imagenes import archivo

AQUI = Path(__file__).resolve().parent
PRODUCTOS = [p for p in json.loads((AQUI.parent / "productos_shopify.json").read_text(encoding="utf-8"))
             if not p.get("exclusivo_web")]
POR_NOMBRE = {p["producto"]: p for p in PRODUCTOS}
NIVELES = [("Bronce", 0.20, 60000), ("Plata", 0.25, 150000), ("Oro", 0.30, 300000)]

# Nombre corto, ficha y argumento de venta para cada producto estrella.
ESTRELLA = [
    ("Protectores Penny Sleeves - Fit 65x90 (100 u.)", "Penny Sleeves Fit",
     "65 × 90 mm · 100 unidades", "El protector que más rota en mesón: Pokémon, Magic y One Piece."),
    ("Protectores Penny Sleeves - Perfect Fit 64x89 (100 u.)", "Penny Sleeves Perfect Fit",
     "64 × 89 mm · 100 unidades", "Ajuste interior para doble enfundado de torneo."),
    ("Protector Over Sleeve Rugosos 69x94", "Over Sleeve Rugoso",
     "69 × 94 mm · exterior mate", "Barajan mejor y aguantan semanas de torneo."),
    ("25 Toploaders 35PT", "Toploaders 35PT",
     "25 unidades · libre de ácido y PVC", "Protección rígida para cartas de valor y envíos."),
    ("Playmate Impermeable Ecocuero", "Playmate Ecocuero",
     "Negro, púrpura o rojo · base antideslizante", "Impermeable: sobrevive bebidas y torneos largos."),
    ("Deck Box - Porta Mazo 80+", "Deck Box 80+",
     "80 cartas enfundadas · negro o azul", "Precio de impulso para la caja registradora."),
    ("Acrílico Magnético - Magnetic Holder 35pt", "Acrílico Magnético",
     "35pt · cierre magnético", "Exhibición premium para cartas de colección."),
    ("Grading Case Nuevo Vacío", "Grading Case",
     "Carcasa vacía tipo graduación", "Para que el cliente arme su propia vitrina."),
]


def clp(n):
    return "$" + f"{round(n):,}".replace(",", ".")


def r10(n):
    return int(round(n / 10) * 10)


def jpeg_liviano(ruta, lado=520):
    """Reduce la foto y la pasa a JPEG sobre el gris del recuadro, para que el PDF pese poco."""
    img = Image.open(ruta)
    img.thumbnail((lado, lado))
    fondo = Image.new("RGB", img.size, (244, 245, 247))
    fondo.paste(img, mask=img.convert("RGBA").split()[-1])
    buf = io.BytesIO()
    fondo.save(buf, "JPEG", quality=78, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def foto(p, clase):
    for f in sorted((AQUI / "img").glob(archivo(p["producto"]) + ".*")):
        return f'<div class="{clase}"><img src="data:image/jpeg;base64,{jpeg_liviano(f)}" alt=""></div>'
    return f'<div class="{clase} vacia"><span>{p["tipo"]}</span></div>'


def precios(p):
    celdas = "".join(f"<div><small>{n}</small><b>{clp(r10(p['pvp'] * (1 - m)))}</b></div>" for n, m, _ in NIVELES)
    return f'<div class="precios"><div class="pvp"><small>Público</small><b>{clp(p["pvp"])}</b></div>{celdas}</div>'


def tarjeta(nombre, corto, ficha, argumento):
    p = POR_NOMBRE[nombre]
    return f"""<article class="card">{foto(p, "foto")}
<div class="info"><h3>{corto}</h3><p class="ficha">{ficha}</p><p class="arg">{argumento}</p>{precios(p)}</div></article>"""


def fila(p):
    estado = f'{p["stock"]} u.' if p["stock"] else "Preventa"
    celdas = "".join(f"<td class=n>{clp(r10(p['pvp'] * (1 - m)))}</td>" for _, m, _ in NIVELES)
    sub = f"<div class=sub>{p['variantes']}</div>" if p["variantes"] else ""
    return (f"<tr><td class=mini>{foto(p, 'thumb')}</td><td><b>{p['producto']}</b>{sub}</td>"
            f"<td class=n>{estado}</td><td class=n>{clp(p['pvp'])}</td>{celdas}</tr>")


estrellas = "".join(tarjeta(*e) for e in ESTRELLA)
nombres_estrella = {e[0] for e in ESTRELLA}
resto = "".join(fila(p) for p in PRODUCTOS if p["producto"] not in nombres_estrella)
niveles = "".join(
    f'<div class="tier"><span>{n}</span><b>{int(m * 100)}<i>%</i></b><small>de margen para tu tienda</small>'
    f'<em>Pedido desde {clp(mn)}</em></div>' for n, m, mn in NIVELES)
cab = ("<tr><th></th><th>Producto</th><th class=n>Stock</th><th class=n>Público</th>"
       + "".join(f"<th class=n>{n}</th>" for n, _, _ in NIVELES) + "</tr>")

html = f"""<!doctype html><html lang=es><meta charset=utf-8><style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font: 10pt/1.45 'Helvetica Neue', Arial, sans-serif; color:#18202b; }}
.page {{ width:210mm; min-height:297mm; padding:14mm 13mm; page-break-after: always; position:relative; }}
.cover {{ background:#141c26; color:#eef1f5; padding:0; }}
.cover .top {{ padding:26mm 16mm 12mm; }}
.cover .kicker {{ letter-spacing:.24em; text-transform:uppercase; font-size:9pt; color:#d9a441; }}
.cover h1 {{ font-size:44pt; line-height:.98; margin:6mm 0 5mm; letter-spacing:-.02em; }}
.cover h1 span {{ color:#d9a441; }}
.cover p.lead {{ font-size:12.5pt; color:#c3ccd8; max-width:150mm; margin:0; }}
.cover .tiers {{ display:flex; gap:5mm; padding:0 16mm; }}
.tier {{ flex:1; background:#1f2a37; border:1px solid #33414f; border-radius:3mm; padding:6mm 5mm; }}
.tier span {{ text-transform:uppercase; letter-spacing:.14em; font-size:8.5pt; color:#9fb0c3; }}
.tier b {{ display:block; font-size:38pt; line-height:1.05; color:#fff; margin-top:2mm; }}
.tier b i {{ font-style:normal; font-size:20pt; color:#d9a441; margin-left:1mm; }}
.tier small {{ display:block; color:#c3ccd8; }}
.tier em {{ display:block; font-style:normal; margin-top:3mm; padding-top:3mm; border-top:1px solid #33414f; font-weight:700; color:#d9a441; }}
.cover .pasos {{ margin:10mm 16mm 0; display:grid; grid-template-columns:repeat(3,1fr); gap:5mm; }}
.paso b {{ display:block; color:#fff; margin-bottom:1mm; }}
.paso {{ color:#aab6c4; font-size:9.5pt; border-top:2px solid #d9a441; padding-top:3mm; }}
.cover .pie {{ position:absolute; left:16mm; right:16mm; bottom:14mm; display:flex; justify-content:space-between; color:#9fb0c3; font-size:9pt; border-top:1px solid #33414f; padding-top:4mm; }}
.cover .pie b {{ color:#fff; }}
h2 {{ font-size:20pt; margin:0 0 1mm; letter-spacing:-.01em; }}
.bajada {{ color:#5b6575; margin:0 0 6mm; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:5mm; }}
.card {{ border:1px solid #dde1e7; border-radius:3mm; overflow:hidden; display:flex; flex-direction:column; break-inside:avoid; }}
.foto {{ height:46mm; background:#f4f5f7; display:flex; align-items:center; justify-content:center; }}
.foto img {{ max-height:42mm; max-width:90%; object-fit:contain; }}
.vacia {{ background: repeating-linear-gradient(135deg,#f1f3f6 0 6px,#e9ecf0 6px 12px); }}
.vacia span {{ text-transform:uppercase; letter-spacing:.14em; font-size:8pt; color:#8a94a3; background:#fff; padding:1mm 3mm; border-radius:2mm; }}
.info {{ padding:4mm 4.5mm 4.5mm; display:flex; flex-direction:column; gap:1mm; flex:1; }}
.info h3 {{ margin:0; font-size:12.5pt; }}
.ficha {{ margin:0; color:#b07a12; font-weight:700; font-size:8.8pt; }}
.arg {{ margin:0 0 2mm; color:#5b6575; font-size:9pt; }}
.precios {{ margin-top:auto; display:grid; grid-template-columns:repeat(4,1fr); border-top:1px solid #dde1e7; padding-top:2.5mm; }}
.precios small {{ display:block; font-size:7.5pt; text-transform:uppercase; letter-spacing:.06em; color:#8a94a3; }}
.precios b {{ font-size:10.5pt; }}
.precios .pvp b {{ color:#8a94a3; text-decoration:line-through; font-weight:400; }}
.precios div:last-child b {{ color:#b07a12; }}
table {{ width:100%; border-collapse:collapse; font-size:9.3pt; }}
th, td {{ padding:2.2mm 2mm; border-bottom:1px solid #e3e6ea; text-align:left; vertical-align:middle; }}
th {{ font-size:7.5pt; text-transform:uppercase; letter-spacing:.06em; color:#5b6575; }}
.n {{ text-align:right; white-space:nowrap; }}
.sub {{ color:#5b6575; font-size:8.3pt; }}
.mini {{ width:16mm; }}
.thumb {{ width:14mm; height:14mm; border-radius:2mm; background:#f4f5f7; display:flex; align-items:center; justify-content:center; overflow:hidden; }}
.thumb img {{ max-width:100%; max-height:100%; object-fit:contain; }}
.thumb.vacia span {{ display:none; }}
.notas {{ margin-top:7mm; display:grid; grid-template-columns:1fr 1fr; gap:6mm; font-size:9pt; color:#3a4452; }}
.notas b {{ display:block; color:#18202b; margin-bottom:1mm; }}
.folio {{ position:absolute; bottom:8mm; left:13mm; right:13mm; display:flex; justify-content:space-between; font-size:8pt; color:#8a94a3; }}
</style>

<section class="page cover">
 <div class="top">
  <div class="kicker">Catálogo mayorista · Octubre 2026</div>
  <h1>Over Power<br>Armor <span>para tiendas</span></h1>
  <p class="lead">Accesorios para cartas coleccionables con stock en Chile. Tu tienda compra con descuento, vende a nuestro precio público sugerido y se queda con el margen.</p>
 </div>
 <div class="tiers">{niveles}</div>
 <div class="pasos">
  <div class="paso"><b>1. Elige tu nivel</b>El monto mínimo se mide a precio público. Puedes combinar todos los productos.</div>
  <div class="paso"><b>2. Haz el pedido</b>En overpowerarmor.cl con tu cuenta de empresa y el código de tu nivel, o por transferencia.</div>
  <div class="paso"><b>3. Recibe en tu local</b>Despacho desde Maipú a todo Chile, o retiro coordinado en Santiago.</div>
 </div>
 <div class="pie"><span><b>overpowerarmor.cl</b> · Maipú, Santiago</span><span>Precios en CLP con IVA · vigentes al 29-10-2026</span></div>
</section>

<section class="page">
 <h2>Productos estrella</h2>
 <p class="bajada">Lo que más se vende en tiendas con torneos. Precio por unidad de venta en cada nivel.</p>
 <div class="grid">{estrellas}</div>
 <div class="folio"><span>Over Power Armor · Catálogo mayorista</span><span>2</span></div>
</section>

<section class="page">
 <h2>Resto del catálogo</h2>
 <p class="bajada">Productos disponibles para tiendas. Los packs y kits son exclusivos de nuestra tienda web.</p>
 <table>{cab}{resto}</table>
 <div class="notas">
  <div><b>Cómo se calcula tu margen</b>Precio tienda = precio público × (1 − margen del nivel). Ejemplo: Penny Sleeves Fit a $2.690 público queda en $1.880 en nivel Oro; ganas $810 por pack.</div>
  <div><b>Contacto</b>overpowerarmor.cl · irsolucioneschile@gmail.com<br>Stock sujeto a disponibilidad; las preventas se despachan al llegar.</div>
 </div>
 <div class="folio"><span>Over Power Armor · Catálogo mayorista</span><span>3</span></div>
</section>
</html>"""

(AQUI / "catalogo_mayorista.html").write_text(html, encoding="utf-8")
print("catalogo_mayorista.html listo")
