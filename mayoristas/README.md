# Over Power Armor · Venta mayorista

Material para vender los accesorios TCG de OPA a tiendas de Chile.

| Archivo | Qué es |
|---|---|
| `tiendas.json` | 299 tiendas en Chile (TCG, juegos de mesa, cómics, anime y hobbies) con dirección, juegos, tipo, canal sugerido, validación y contacto cuando se encontró: correo (31), Instagram (45) y WhatsApp (17). |
| `fuentes/` | Lotes de tiendas encontradas (`lote2.tsv`), correos e Instagram/WhatsApp con su fuente (`emails.json`, `contactos.json`) y el script que los fusiona sin duplicar (`fusionar.py`). |
| `presentacion/` | Catálogo mayorista en PDF (`Catalogo_Mayorista_OPA.pdf`) y los emails de presentación personalizados, aún sin enviar (`emails_pendientes.json`). |
| `productos_shopify.json` | Foto de los productos activos de overpowerarmor.cl al 29-10-2026 (PVP, costo, stock, peso en kg). |
| `generar_catalogo.py` | Genera `catalogo_mayorista.csv` con los precios para tiendas en 3 niveles. |
| `catalogo_mayorista.csv` | Catálogo listo para abrir en Excel (separador `;`). |
| `dashboard.html` | Fuente del dashboard publicado. Lee `tiendas.json` publicado junto a la página y guarda el estado de cada contacto en su base de datos. |

## Niveles mayoristas

Precio tienda = PVP × (1 − margen). La tienda vende al PVP y se queda con el margen.

| Nivel | Margen tienda | Pedido mínimo (a PVP) | Código Shopify |
|---|---|---|---|
| Bronce | 20 % | $60.000 | `MAYORISTA20` |
| Plata | 25 % | $150.000 | `MAYORISTA25` |
| Oro | 30 % | $300.000 | `MAYORISTA30` |

Los códigos solo funcionan para clientes del segmento «Clientes añadidos a empresas».

## Validación de tiendas

- **Sitio web activo**: la web propia de la tienda aparece indexada hoy.
- **Directorio TorneosTCG**: tiene ficha y calendario de torneos en torneostcg.cl.
- **Por confirmar**: solo aparece en listas de distribuidores (Devir, Mitos y Leyendas); confirmar antes de visitar.

## Regenerar el catálogo

```bash
python3 mayoristas/generar_catalogo.py
```

## Regenerar la presentación

```bash
python3 mayoristas/presentacion/generar_catalogo_html.py
node mayoristas/presentacion/a_pdf.js
python3 mayoristas/presentacion/generar_emails.py
```

`generar_emails.py` solo arma los textos: no envía correos.
