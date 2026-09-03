"""
App de escritorio (Tkinter) para imprimir en una impresora térmica NO-Zebra
las etiquetas de producto que Mercado Libre exporta en formato ZPL (.txt).

Flujo:
  1. Abrís el archivo .txt con el ZPL.
  2. La app extrae código de barras, descripción y SKU de cada etiqueta, y
     agrupa las repetidas mostrando la cantidad a imprimir.
  3. Elegís cómo está conectada la impresora (recomendado en Windows:
     "Impresora de Windows", usando el driver que ya tenés instalado).
  4. Imprimís todo el lote, o seleccionás filas puntuales.

Requisitos: Python 3.9+, `pip install python-escpos` (y en Windows,
`pip install pywin32` para el backend "Impresora de Windows").
"""

from __future__ import annotations

import platform
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from printer_backend import (
    PrinterConfig,
    PrinterSetupError,
    list_windows_printers,
    open_printer,
    print_group,
)
from zpl_parser import LabelGroup, group_labels, parse_zpl_file

BACKEND_LABELS = {
    "win32": "Impresora de Windows (recomendado en Windows)",
    "usb": "USB directo (Vendor/Product ID)",
    "file": "Dispositivo Linux (/dev/usb/lp0)",
    "dummy": "Prueba: guardar en archivo .bin (sin imprimir)",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Etiquetas ML → Impresora térmica")
        self.geometry("980x620")

        self.groups: list[LabelGroup] = []
        self.log_queue: "queue.Queue[str]" = queue.Queue()

        self._build_ui()
        self._poll_log_queue()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Button(top, text="Abrir ZPL (.txt)…", command=self.on_open_file).pack(side="left")
        self.file_label = ttk.Label(top, text="Ningún archivo cargado")
        self.file_label.pack(side="left", padx=10)

        # --- tabla de etiquetas -------------------------------------------------
        columns = ("codigo", "sku", "cantidad", "descripcion")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
        for col, title, width in [
            ("codigo", "Código de barras", 140),
            ("sku", "SKU", 140),
            ("cantidad", "Cantidad", 80),
            ("descripcion", "Descripción", 500),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)
        self.tree.bind("<Double-1>", self.on_edit_quantity)

        hint = ttk.Label(
            self,
            text="Doble clic sobre la cantidad para corregirla antes de imprimir.",
            foreground="#666",
        )
        hint.pack(anchor="w", padx=8)

        # --- configuración de impresora ------------------------------------------
        cfg = ttk.LabelFrame(self, text="Impresora", padding=8)
        cfg.pack(fill="x", padx=8, pady=6)

        ttk.Label(cfg, text="Ancho del rollo:").grid(row=0, column=0, sticky="w")
        self.ancho_var = tk.StringVar(value="80")
        ttk.Combobox(
            cfg, textvariable=self.ancho_var, values=["58", "80"], width=6, state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(cfg, text="mm").grid(row=0, column=2, sticky="w")

        ttk.Label(cfg, text="Conexión:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        default_backend = "win32" if platform.system() == "Windows" else "dummy"
        self.backend_var = tk.StringVar(value=default_backend)
        backend_combo = ttk.Combobox(
            cfg,
            textvariable=self.backend_var,
            values=list(BACKEND_LABELS.keys()),
            state="readonly",
            width=12,
        )
        backend_combo.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        backend_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_backend_fields())

        self.backend_desc = ttk.Label(cfg, text=BACKEND_LABELS[default_backend], foreground="#666")
        self.backend_desc.grid(row=1, column=2, columnspan=3, sticky="w", pady=(6, 0))

        # Campos específicos por backend (se muestran/ocultan dinámicamente)
        self.backend_fields_frame = ttk.Frame(cfg)
        self.backend_fields_frame.grid(row=2, column=0, columnspan=5, sticky="we", pady=(6, 0))

        self.win32_printer_var = tk.StringVar()
        self.usb_vendor_var = tk.StringVar(value="0x0000")
        self.usb_product_var = tk.StringVar(value="0x0000")
        self.file_path_var = tk.StringVar(value="/dev/usb/lp0")
        self.dummy_path_var = tk.StringVar(value="etiquetas_escpos.bin")

        self._refresh_backend_fields()

        # --- botones de acción ----------------------------------------------------
        actions = ttk.Frame(self, padding=8)
        actions.pack(fill="x")
        ttk.Button(actions, text="Probar conexión", command=self.on_test_connection).pack(side="left")
        ttk.Button(actions, text="Imprimir seleccionadas", command=self.on_print_selected).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Imprimir todo", command=self.on_print_all).pack(side="left")

        # --- log -------------------------------------------------------------------
        self.log_text = tk.Text(self, height=8, state="disabled", bg="#111", fg="#0f0")
        self.log_text.pack(fill="both", padx=8, pady=(0, 8))

    def _refresh_backend_fields(self):
        for w in self.backend_fields_frame.winfo_children():
            w.destroy()
        backend = self.backend_var.get()
        self.backend_desc.config(text=BACKEND_LABELS.get(backend, ""))

        if backend == "win32":
            ttk.Label(self.backend_fields_frame, text="Nombre de la impresora:").grid(
                row=0, column=0, sticky="w"
            )
            names = list_windows_printers()
            combo = ttk.Combobox(
                self.backend_fields_frame, textvariable=self.win32_printer_var, values=names, width=40
            )
            combo.grid(row=0, column=1, sticky="w", padx=4)
            if names and not self.win32_printer_var.get():
                self.win32_printer_var.set(names[0])
        elif backend == "usb":
            ttk.Label(self.backend_fields_frame, text="Vendor ID (hex):").grid(row=0, column=0, sticky="w")
            ttk.Entry(self.backend_fields_frame, textvariable=self.usb_vendor_var, width=10).grid(
                row=0, column=1, sticky="w", padx=4
            )
            ttk.Label(self.backend_fields_frame, text="Product ID (hex):").grid(
                row=0, column=2, sticky="w", padx=(10, 0)
            )
            ttk.Entry(self.backend_fields_frame, textvariable=self.usb_product_var, width=10).grid(
                row=0, column=3, sticky="w", padx=4
            )
        elif backend == "file":
            ttk.Label(self.backend_fields_frame, text="Ruta del dispositivo:").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Entry(self.backend_fields_frame, textvariable=self.file_path_var, width=30).grid(
                row=0, column=1, sticky="w", padx=4
            )
        elif backend == "dummy":
            ttk.Label(self.backend_fields_frame, text="Guardar como:").grid(row=0, column=0, sticky="w")
            ttk.Entry(self.backend_fields_frame, textvariable=self.dummy_path_var, width=30).grid(
                row=0, column=1, sticky="w", padx=4
            )

    # ------------------------------------------------------------- callbacks

    def on_open_file(self):
        path = filedialog.askopenfilename(
            title="Elegí el archivo ZPL (.txt) de Mercado Libre",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            labels = parse_zpl_file(path)
            self.groups = group_labels(labels)
        except Exception as exc:
            messagebox.showerror("Error al leer el archivo", str(exc))
            return

        if not self.groups:
            messagebox.showwarning(
                "Sin etiquetas",
                "No se encontró ninguna etiqueta reconocible en ese archivo. "
                "¿Es un .txt con ZPL exportado de Mercado Libre?",
            )

        self.file_label.config(text=path.split("/")[-1].split("\\")[-1])
        self._populate_tree()
        self._log(
            f"Cargadas {len(self.groups)} etiquetas distintas "
            f"({sum(g.quantity for g in self.groups)} unidades en total)."
        )

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, g in enumerate(self.groups):
            self.tree.insert(
                "", "end", iid=str(i), values=(g.code, g.sku, g.quantity, g.description)
            )

    def on_edit_quantity(self, event):
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item_id or col != "#3":  # columna "cantidad"
            return
        idx = int(item_id)
        current = self.groups[idx].quantity
        new_val = simpledialog.askinteger(
            "Cantidad", f"Cantidad a imprimir para {self.groups[idx].code}:", initialvalue=current, minvalue=0
        )
        if new_val is not None:
            self.groups[idx].quantity = new_val
            self._populate_tree()

    def _build_printer_config(self) -> PrinterConfig:
        backend = self.backend_var.get()
        if backend == "win32":
            return PrinterConfig(backend="win32", printer_name=self.win32_printer_var.get() or None)
        if backend == "usb":
            try:
                vid = int(self.usb_vendor_var.get(), 16)
                pid = int(self.usb_product_var.get(), 16)
            except ValueError:
                raise PrinterSetupError("Vendor ID / Product ID deben ser hexadecimales, ej. 0x04b8.")
            return PrinterConfig(backend="usb", vendor_id=vid, product_id=pid)
        if backend == "file":
            return PrinterConfig(backend="file", device_path=self.file_path_var.get())
        return PrinterConfig(backend="dummy", dummy_output_path=self.dummy_path_var.get())

    def on_test_connection(self):
        try:
            config = self._build_printer_config()
            printer = open_printer(config)
            try:
                close = getattr(printer, "close", None)
                if close:
                    close()
            except Exception:
                pass
            messagebox.showinfo("Conexión OK", "Se pudo abrir la impresora correctamente.")
        except PrinterSetupError as exc:
            messagebox.showerror("No se pudo conectar", str(exc))
        except Exception as exc:
            messagebox.showerror("Error inesperado", str(exc))

    def on_print_selected(self):
        idxs = [int(i) for i in self.tree.selection()]
        if not idxs:
            messagebox.showinfo("Nada seleccionado", "Seleccioná al menos una fila de la tabla.")
            return
        self._print_groups([self.groups[i] for i in idxs])

    def on_print_all(self):
        if not self.groups:
            messagebox.showinfo("Sin datos", "Primero abrí un archivo ZPL.")
            return
        self._print_groups(self.groups)

    def _print_groups(self, groups: list[LabelGroup]):
        try:
            ancho_mm = int(self.ancho_var.get())
            config = self._build_printer_config()
        except PrinterSetupError as exc:
            messagebox.showerror("Configuración inválida", str(exc))
            return

        thread = threading.Thread(target=self._print_worker, args=(groups, ancho_mm, config), daemon=True)
        thread.start()

    def _print_worker(self, groups: list[LabelGroup], ancho_mm: int, config: PrinterConfig):
        try:
            printer = open_printer(config)
        except PrinterSetupError as exc:
            self.log_queue.put(f"ERROR: {exc}")
            return

        total = sum(g.quantity for g in groups)
        self.log_queue.put(f"Imprimiendo {len(groups)} producto(s), {total} etiqueta(s) en total…")
        done = 0
        try:
            for g in groups:
                print_group(printer, g, ancho_mm)
                done += g.quantity
                self.log_queue.put(f"  OK: {g.code} x{g.quantity} ({done}/{total})")

            if config.backend == "dummy":
                data = getattr(printer, "output", b"")
                path = config.dummy_output_path or "etiquetas_escpos.bin"
                with open(path, "wb") as f:
                    f.write(data)
                self.log_queue.put(f"Guardado en {path} ({len(data)} bytes). No se envió a ninguna impresora.")

            self.log_queue.put("Listo.")
        except Exception as exc:
            self.log_queue.put(f"ERROR durante la impresión: {exc}")
        finally:
            close = getattr(printer, "close", None)
            if close:
                try:
                    close()
                except Exception:
                    pass

    # ------------------------------------------------------------------- log

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)


if __name__ == "__main__":
    App().mainloop()
