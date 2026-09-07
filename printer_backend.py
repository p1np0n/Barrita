"""
Capa de impresión ESC/POS, encima de la librería `python-escpos`.

Se importa `escpos` de forma perezosa (dentro de las funciones) para que el
resto de la app (parseo del ZPL, la grilla de la GUI) funcione igual aunque
todavía no se haya instalado `python-escpos` en la máquina.

Backends soportados:
  - "usb"    -> conexión USB directa (Linux/Mac, o Windows con driver
                libusb/Zadig instalado). Requiere Vendor ID y Product ID.
  - "win32"  -> impresora ya instalada en Windows (Panel de impresoras).
                Usa la cola de impresión de Windows con el driver que ya
                esté configurado (no requiere Zadig). Es la opción
                recomendada en Windows.
  - "file"   -> dispositivo de caracteres crudo en Linux, típicamente
                /dev/usb/lp0 (impresora USB reconocida por el kernel sin
                necesidad de libusb).
  - "dummy"  -> no imprime nada: guarda los bytes ESC/POS generados en un
                archivo .bin, para probar la app sin tener la impresora a
                mano.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Optional

from label_render import build_label_text_block
from zpl_parser import LabelGroup


class PrinterSetupError(RuntimeError):
    """Error de configuración de impresora, con mensaje ya listo para el usuario."""


@dataclass
class PrinterConfig:
    backend: str  # "usb" | "win32" | "file" | "dummy"
    vendor_id: Optional[int] = None      # ej. 0x04b8 (Epson) -- solo backend "usb"
    product_id: Optional[int] = None     # ej. 0x0202          -- solo backend "usb"
    printer_name: Optional[str] = None   # nombre exacto en Windows -- solo backend "win32"
    device_path: Optional[str] = None    # ej. /dev/usb/lp0 -- solo backend "file"
    dummy_output_path: Optional[str] = None  # archivo .bin de salida -- solo backend "dummy"


def _require_escpos():
    try:
        import escpos  # noqa: F401
    except ImportError as exc:
        raise PrinterSetupError(
            "Falta instalar la librería 'python-escpos'. "
            "Corré: pip install python-escpos"
        ) from exc


def open_printer(config: PrinterConfig):
    """Abre y devuelve un objeto impresora de python-escpos según el backend elegido."""
    _require_escpos()
    from escpos.printer import Dummy, File, Usb, Win32Raw

    if config.backend == "usb":
        if config.vendor_id is None or config.product_id is None:
            raise PrinterSetupError("Faltan Vendor ID / Product ID para la conexión USB.")
        try:
            return Usb(config.vendor_id, config.product_id, 0)
        except Exception as exc:  # pyusb / permisos / driver
            raise PrinterSetupError(
                "No se pudo abrir la impresora por USB. En Windows necesitás "
                "reemplazar el driver del puerto USB de la impresora por 'libusb-win32' "
                "usando la herramienta Zadig (https://zadig.akeo.ie/) -- ojo que esto "
                "puede sacarla de la cola de impresión normal de Windows. Si preferís "
                "no tocar el driver, instalá la impresora normalmente en Windows y "
                "usá el backend 'win32' en su lugar.\n\nDetalle técnico: "
                f"{exc}"
            ) from exc

    if config.backend == "win32":
        if platform.system() != "Windows":
            raise PrinterSetupError("El backend 'win32' solo funciona en Windows.")
        try:
            return Win32Raw(config.printer_name)
        except Exception as exc:
            raise PrinterSetupError(
                "No se pudo abrir la impresora de Windows "
                f"'{config.printer_name}'. Verificá el nombre exacto en "
                "Configuración > Impresoras y escáneres.\n\nDetalle técnico: "
                f"{exc}"
            ) from exc

    if config.backend == "file":
        if not config.device_path:
            raise PrinterSetupError("Falta la ruta del dispositivo (ej. /dev/usb/lp0).")
        try:
            return File(config.device_path)
        except Exception as exc:
            raise PrinterSetupError(
                f"No se pudo abrir el dispositivo '{config.device_path}'. "
                "Verificá que la impresora esté conectada y que tengas permisos "
                "de lectura/escritura sobre ese archivo (grupo 'lp' en Linux).\n\n"
                f"Detalle técnico: {exc}"
            ) from exc

    if config.backend == "dummy":
        return Dummy()

    raise PrinterSetupError(f"Backend desconocido: {config.backend!r}")


def list_windows_printers() -> list[str]:
    """Lista los nombres de impresoras instaladas en Windows (para poblar la GUI)."""
    if platform.system() != "Windows":
        return []
    try:
        import win32print
    except ImportError:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def print_group(
    printer,
    group: LabelGroup,
    ancho_mm: float,
    copies: Optional[int] = None,
    alto_mm: Optional[float] = None,
    cut: bool = True,
    barcode_height: int = 64,
) -> None:
    """Imprime `copies` etiquetas (por defecto, la cantidad detectada en el ZPL).

    `alto_mm` es opcional: si se especifica (etiqueta troquelada de alto
    fijo, ej. 25mm), se usa para no meter más líneas de descripción de las
    que entran antes de la etiqueta siguiente. `cut` controla si se manda el
    comando de corte de papel (GS V) después de cada etiqueta -- muchas
    impresoras de etiquetas chicas no tienen cuchilla automática (usan
    despegado manual) y algunas se cuelgan o ignoran el resto del trabajo si
    reciben ese comando sin soportarlo, así que conviene poder desactivarlo.
    """
    n = group.quantity if copies is None else copies
    text_lines = build_label_text_block(group, ancho_mm, alto_mm)

    # python-escpos exige el "code set" de CODE128 como prefijo del dato
    # ({A/{B/{C) -- si no, el comando ESC/POS queda mal formado y la
    # impresora lo rechaza o lo imprime en blanco. Usamos {B (Code Set B:
    # cualquier ASCII imprimible) porque los códigos de ML no siempre son
    # puramente numéricos de largo par, que es lo único que acepta {C.
    barcode_data = f"{{B{group.code}"

    for _ in range(max(0, n)):
        printer.set(align="center")
        printer.barcode(
            barcode_data,
            "CODE128",
            height=barcode_height,
            width=2,
            pos="BELOW",   # imprime el texto legible del código debajo de las barras
            align_ct=True,
        )
        printer.set(align="center", bold=False)
        for line in text_lines:
            printer.text(line + "\n")
        printer.text("\n")
        if cut:
            printer.cut()


def print_batch(
    printer,
    groups: list[LabelGroup],
    ancho_mm: float,
    alto_mm: Optional[float] = None,
    cut: bool = True,
    barcode_height: int = 64,
) -> None:
    for g in groups:
        print_group(printer, g, ancho_mm, alto_mm=alto_mm, cut=cut, barcode_height=barcode_height)


def print_test_label(printer, ancho_mm: float = 50, cut: bool = True) -> None:
    """Imprime una etiqueta simple de solo texto (sin código de barras).

    Sirve para probar que la conexión con la impresora funciona de punta a
    punta sin depender del comando de código de barras: si esto tampoco
    imprime nada, el problema está en la conexión/driver, no en el ZPL ni en
    el formato del barcode.
    """
    printer.set(align="center", bold=True)
    printer.text("PRUEBA DE IMPRESION\n")
    printer.set(align="center", bold=False)
    printer.text(f"Ancho configurado: {ancho_mm}mm\n")
    printer.text("Si ves este texto, la conexion funciona.\n")
    printer.text("\n")
    if cut:
        printer.cut()


def render_batch_to_dummy_bytes(
    groups: list[LabelGroup],
    ancho_mm: float,
    alto_mm: Optional[float] = None,
    cut: bool = True,
    barcode_height: int = 64,
) -> bytes:
    """Genera los bytes ESC/POS del trabajo completo sin enviarlos a ninguna impresora."""
    _require_escpos()
    from escpos.printer import Dummy

    dummy = Dummy()
    print_batch(dummy, groups, ancho_mm, alto_mm=alto_mm, cut=cut, barcode_height=barcode_height)
    return dummy.output
