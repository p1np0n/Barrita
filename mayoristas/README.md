# Over Power Armor · Venta mayorista

Material para vender los accesorios TCG de OPA a tiendas de Chile.

| Archivo | Qué es |
|---|---|
| `tiendas.json` | 56 tiendas TCG en Chile (18 prioridad A, 24 B, 14 C) con dirección, juegos, canal sugerido y nivel de validación. |
| `productos_shopify.json` | Foto de los productos activos de overpowerarmor.cl al 29-10-2026 (PVP, costo, stock, peso en kg). |
| `generar_catalogo.py` | Genera `catalogo_mayorista.csv` con los precios para tiendas en 3 niveles. |
| `catalogo_mayorista.csv` | Catálogo listo para abrir en Excel (separador `;`). |
| `dashboard.html` | Fuente del dashboard publicado (embudo, catálogo, cotizador y mensajes). |

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
