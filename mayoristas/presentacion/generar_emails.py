"""Arma el email de presentación para cada tienda con correo en tiendas.json.

Salida: emails_pendientes.json (destinatario, asunto, cuerpo HTML y texto).
Cada email enlaza el catálogo PDF publicado en los archivos de Shopify (CATALOGO_URL).
No envía nada: los correos se crean como borradores solo cuando el dueño lo aprueba.
"""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TIENDAS = json.loads((AQUI.parent / "tiendas.json").read_text(encoding="utf-8"))
PRODUCTOS = {p["producto"]: p for p in json.loads((AQUI.parent / "productos_shopify.json").read_text(encoding="utf-8"))}
ESTRELLA = [
    "Protectores Penny Sleeves - Fit 65x90 (100 u.)",
    "Protector Over Sleeve Rugosos 69x94",
    "25 Toploaders 35PT",
    "Playmate Impermeable Ecocuero",
    "Deck Box - Porta Mazo 80+",
    "Acrílico Magnético - Magnetic Holder 35pt",
]
CATALOGO_URL = "https://cdn.shopify.com/s/files/1/0938/1213/0164/files/Catalogo_Mayorista_OPA.pdf?v=1793379066"
ASUNTO = "Accesorios TCG al por mayor para {tienda}: 20 % a 30 % de margen"


def clp(n):
    return "$" + f"{round(n):,}".replace(",", ".")


def r10(n):
    return int(round(n / 10) * 10)


def tabla_html():
    filas = "".join(
        f"<tr><td style='padding:6px 8px;border-bottom:1px solid #e3e6ea'>{n}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e3e6ea;text-align:right'>{clp(PRODUCTOS[n]['pvp'])}</td>"
        f"<td style='padding:6px 8px;border-bottom:1px solid #e3e6ea;text-align:right'><b>{clp(r10(PRODUCTOS[n]['pvp']*0.7))}</b></td></tr>"
        for n in ESTRELLA)
    return ("<table style='border-collapse:collapse;font-size:14px;width:100%;max-width:560px'>"
            "<tr><th style='text-align:left;padding:6px 8px;color:#5b6575'>Producto</th>"
            "<th style='text-align:right;padding:6px 8px;color:#5b6575'>Precio público</th>"
            "<th style='text-align:right;padding:6px 8px;color:#5b6575'>Tu precio (Oro 30 %)</th></tr>"
            f"{filas}</table>")


def tabla_texto():
    return "\n".join(f"- {n}: público {clp(PRODUCTOS[n]['pvp'])} / tienda nivel Oro {clp(r10(PRODUCTOS[n]['pvp']*0.7))}" for n in ESTRELLA)


def cuerpo_html(tienda):
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;color:#18202b">
<p>Hola equipo de {tienda}:</p>
<p>Les escribimos desde <b>Over Power Armor</b> (<a href="https://overpowerarmor.cl">overpowerarmor.cl</a>), marca chilena de accesorios para cartas coleccionables. Despachamos desde Maipú a todo Chile.</p>
<p>Estamos abriendo venta mayorista para tiendas TCG, con precios que les dejan <b>entre 20 % y 30 % de margen</b> vendiendo a nuestro precio público:</p>
<ul>
<li><b>Bronce:</b> 20 % de margen, pedido desde $60.000</li>
<li><b>Plata:</b> 25 % de margen, desde $150.000</li>
<li><b>Oro:</b> 30 % de margen, desde $300.000</li>
</ul>
<p><b>Nuestros productos estrella</b> (precios con IVA):</p>
{tabla_html()}
<p>También tenemos penny sleeves 64x89 y 69x94, grading cases, bases acrílicas, hojas para archivador y porta playmates. El catálogo trae fotos, fichas y los precios de los tres niveles:</p>
<p><a href="{CATALOGO_URL}" style="display:inline-block;background:#b07a12;color:#ffffff;text-decoration:none;font-weight:bold;padding:10px 18px;border-radius:6px">Ver catálogo mayorista (PDF)</a></p>
<p>Si prefieren, pasamos a dejarles muestras.</p>
<p>¿Les acomoda que conversemos esta semana?</p>
<p>Saludos,<br>Equipo Over Power Armor<br>overpowerarmor.cl</p>
</div>"""


def cuerpo_texto(tienda):
    return f"""Hola equipo de {tienda}:

Les escribimos desde Over Power Armor (overpowerarmor.cl), marca chilena de accesorios para cartas coleccionables. Despachamos desde Maipú a todo Chile.

Estamos abriendo venta mayorista para tiendas TCG, con precios que les dejan entre 20 % y 30 % de margen vendiendo a nuestro precio público:
- Bronce: 20 % de margen, pedido desde $60.000
- Plata: 25 % de margen, desde $150.000
- Oro: 30 % de margen, desde $300.000

Nuestros productos estrella (precios con IVA):
{tabla_texto()}

También tenemos penny sleeves 64x89 y 69x94, grading cases, bases acrílicas, hojas para archivador y porta playmates. Catálogo mayorista con fotos y precios de los tres niveles:
{CATALOGO_URL}

Si prefieren, pasamos a dejarles muestras.

¿Les acomoda que conversemos esta semana?

Saludos,
Equipo Over Power Armor
overpowerarmor.cl"""


def main():
    vistos, salida = set(), []
    for t in TIENDAS:
        # Las tiendas marcadas como competencia no reciben la oferta mayorista.
        if not t.get("email") or t["email"] in vistos or t.get("competencia") or t.get("excluir_correo"):
            continue
        vistos.add(t["email"])
        nombre = t["nombre"].replace("Magicsur Los Dominicos", "Magicsur")
        salida.append({"tienda": nombre, "to": t["email"], "subject": ASUNTO.format(tienda=nombre),
                       "html": cuerpo_html(nombre), "text": cuerpo_texto(nombre)})
    (AQUI / "emails_pendientes.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(salida)} emails listos (sin enviar)")


if __name__ == "__main__":
    main()
