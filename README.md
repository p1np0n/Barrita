# Etiquetas ML → Impresora térmica (no Zebra)

App de escritorio para tomar el archivo `.txt` con ZPL que exporta Mercado
Libre (etiquetas de producto/SKU) e imprimirlo en una impresora térmica común
(no Zebra) conectada por USB, sin necesidad de que la impresora entienda ZPL.

**Importante:** este `.txt` (`Envio75713913Etiquetasdeproductos.txt`) trae las
**etiquetas de producto** (código de barras interno + nombre + SKU) que
Mercado Libre genera para identificar cada artículo dentro del paquete — no
es la **etiqueta de envío** (la guía que pega el correo/agencia, con el QR y
los datos del comprador). Son dos PDFs/ZPL distintos que ML genera por
separado. Esta app está armada para el archivo de etiquetas de producto que
subiste; si más adelante también necesitás imprimir la etiqueta de envío en
la térmica, avisame — el enfoque cambia un poco porque esa etiqueta lleva un
código QR y un layout más denso.

## Qué hace

1. Lee el `.txt` y extrae de cada etiqueta: código de barras, descripción del
   producto y SKU (decodificando los acentos que Mercado Libre manda
   escapados en hexadecimal, ej. `Espa_C3_B1ol` → `Español`).
2. Agrupa las etiquetas repetidas y te muestra cuántas copias hay que
   imprimir de cada producto.
3. Genera el código de barras de forma **nativa en la impresora** (comando
   ESC/POS `GS k`, formato Code128) en vez de convertir una imagen — queda
   más nítido y se lee mejor con el lector del correo.
4. Imprime por USB, ya sea:
   - usando la impresora tal cual quedó instalada en Windows (recomendado,
     no requiere tocar drivers), o
   - hablándole directo al dispositivo USB (Linux/Mac, o Windows con Zadig).

## Instalación

Necesitás [Python 3.9 o superior](https://www.python.org/downloads/)
instalado (en Windows, al instalar tildá la opción "Add python.exe to PATH").

```bash
cd ml-barcode-app
pip install -r requirements.txt
```

Esto instala `python-escpos` (la librería que arma los comandos ESC/POS) y,
en Windows, `pywin32` (para hablar con la cola de impresión de Windows).

## Uso

```bash
python app.py
```

1. **Abrir ZPL (.txt)…** → elegí el archivo que exporta Mercado Libre.
2. Revisá la tabla: código, SKU, cantidad y descripción de cada producto.
   Si la cantidad no coincide con lo que necesitás imprimir, hacé doble clic
   sobre el número para corregirlo.
3. En **Impresora**:
   - **Ancho del rollo**: 58 o 80 mm (el ancho físico del papel que usa tu
     impresora — medilo si no lo sabés seguro).
   - **Conexión**: en Windows, dejá "Impresora de Windows" y elegí el nombre
     que aparece en el desplegable (es el mismo nombre que ves en
     *Configuración → Impresoras y escáneres*). Si tu impresora todavía no
     aparece ahí, instalala primero con el driver del fabricante (o el
     genérico "Generic / Text Only" de Windows) — una vez que imprime un
     ticket de prueba desde Windows, ya va a andar acá también.
4. **Probar conexión** para confirmar que la app puede abrir la impresora
   antes de gastar papel.
5. **Imprimir todo** (o seleccioná filas puntuales y **Imprimir
   seleccionadas**).

### Probar sin tener la impresora a mano

Elegí la conexión **"Prueba: guardar en archivo .bin"**. La app arma todo el
trabajo de impresión (códigos de barra + texto) y lo guarda en un archivo en
vez de mandarlo a una impresora, para que puedas revisar que el parseo del
ZPL da lo esperado antes de conectar el hardware.

## Si tu impresora se conecta por USB "crudo" (sin driver de Windows)

Algunas impresoras térmicas baratas no traen driver de Windows y solo se
pueden hablar directo por USB. Para eso:

- **Windows**: instalá [Zadig](https://zadig.akeo.ie/), abrí Options →
  List All Devices, seleccioná tu impresora en el desplegable y reemplazá su
  driver por `libusb-win32` (botón "Replace Driver" / "Install Driver").
  Zadig te muestra ahí mismo el **Vendor ID (VID)** y **Product ID (PID)**
  del dispositivo, en formato `0x04B8` — copialos tal cual. Después, en la
  app, elegí conexión **"USB directo"** y completá esos dos valores. Ojo:
  esto saca la impresora de la cola de impresión normal de Windows — no vas
  a poder imprimir tickets desde otros programas (ni usar el backend
  "Impresora de Windows") mientras tenga ese driver instalado; si querés
  volver atrás, desinstalá el driver desde el Administrador de dispositivos
  y Windows vuelve a instalar el driver original.
- **Linux**: normalmente aparece sola como `/dev/usb/lp0`. Elegí conexión
  **"Dispositivo Linux"** y esa ruta (puede que necesites agregarte al grupo
  `lp`: `sudo usermod -aG lp $USER`, y reiniciar sesión).

## Convertirla en un .exe (opcional, para no depender de tener Python instalado)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

El ejecutable queda en `dist/app.exe`.

## Estructura del proyecto

```
zpl_parser.py       # extrae código de barras / descripción / SKU del ZPL
label_render.py      # arma el texto de la etiqueta (wrap de la descripción)
printer_backend.py   # conexión con la impresora (python-escpos)
app.py                # interfaz gráfica (Tkinter)
```
