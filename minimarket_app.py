import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import os
import sys
import platform
from PIL import Image, ImageTk

OS = platform.system()  # "Windows", "Darwin" (macOS), "Linux"

# --- CONFIGURACIÓN DE DB ---
def obtener_ruta_db():
    if getattr(sys, 'frozen', False):
        ruta_exe = os.path.dirname(sys.executable)
        base_path = os.path.abspath(os.path.join(ruta_exe, "../../..")) if "Contents/MacOS" in ruta_exe else ruta_exe
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "productos.db")

DB_PATH = obtener_ruta_db()

ctk.set_appearance_mode("light")  # tema gris claro
ctk.set_default_color_theme("blue")

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)  # sin borde ni barra de título

        # Centrar en pantalla
        w, h = 420, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(fg_color="white")
        self.lift()
        self.attributes("-topmost", True)

        # Logo
        try:
            base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            img = Image.open(os.path.join(base, "KitoLogo.png")).resize((200, 200), Image.LANCZOS)
            self._logo = ImageTk.PhotoImage(img)
            ctk.CTkLabel(self, image=self._logo, text="").pack(pady=(40, 10))
        except Exception:
            ctk.CTkLabel(self, text="🏪", font=("Arial", 80)).pack(pady=(40, 10))

        ctk.CTkLabel(self, text="KitoMarket Pro", font=("Arial", 22, "bold"), text_color="#2ecc71").pack()
        ctk.CTkLabel(self, text="Cargando...", font=("Arial", 12), text_color="gray").pack(pady=(6, 0))


class MinimarketApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KitoMarket Pro")
        try:
            base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            if OS == "Windows":
                self.iconbitmap(os.path.join(base, "KitoLogo.ico"))
            elif OS == "Linux":
                icon = ImageTk.PhotoImage(Image.open(os.path.join(base, "KitoLogo.png")).resize((64, 64)))
                self.iconphoto(True, icon)
            # macOS: el ícono lo maneja el .icns del bundle, no hace falta código
        except Exception:
            pass
        self.ventana_abierta = None
        self.codigo_actual = None
        self.historial_data = []
        self._proteger_emergente = False
        self._tiempo_proteccion = 500 if OS == "Windows" else 200

        # --- Validadores ---
        self._val_num    = self.register(lambda s: s.isdigit() or s == "")
        self._val_precio = self.register(lambda s: (s.isdigit() or s == "") and len(s) <= 6)

        # --- Arrancar centrado y adaptado a la pantalla actual ---
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("1024x768")
        self.minsize(600, 450)
        self.resizable(True, True)
        # Fullscreen según sistema operativo
        if OS == "Windows":
            self.after(10, lambda: self.state('zoomed'))
        elif OS == "Darwin":
            self.after(10, lambda: self.state('zoomed'))
        else:  # Linux
            self.after(10, lambda: self.attributes('-zoomed', True))

        self.protocol("WM_DELETE_WINDOW", self.confirmar_salida)
        self.bind("<FocusIn>", self._on_focus_principal)
        self.bind("<Configure>", self._on_resize)

        # --- ESTRUCTURA ---

        # 1. Barra Superior
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(side="top", fill="x", padx=20, pady=10)

        self.btn_reg = ctk.CTkButton(self.top_bar, text="➕ REGISTRAR", fg_color="#2ecc71", width=160, height=45, font=("Arial", 14, "bold"), command=self.abrir_ventana_registro)
        self.btn_reg.pack(side="left")

        self.btn_bus = ctk.CTkButton(self.top_bar, text="🔍 BUSCADOR", fg_color="#3498db", width=160, height=45, font=("Arial", 14, "bold"), command=self.abrir_ventana_busqueda)
        self.btn_bus.pack(side="right")

        # 2. Contenedor Principal (Visor)
        self.visor = ctk.CTkFrame(self, fg_color="transparent")
        self.visor.pack(expand=True, fill="both")
        self.visor.bind("<Button-1>", lambda e: self.cerrar_emergente_si_existe())

        self.lbl_guia = ctk.CTkLabel(self.visor, text="ESCANEE EL PRODUCTO AQUÍ", font=("Arial", 16, "bold"), text_color="gray")
        self.lbl_guia.pack(pady=(6, 0))

        self.entry_scan = ctk.CTkEntry(self.visor, font=("Arial", 36, "bold"), justify="center", width=400, height=65,
                                       validate="key", validatecommand=(self._val_num, "%P"))
        self.entry_scan.pack(pady=8)
        self.entry_scan.bind("<Return>", self.buscar_barras)

        self.lbl_nombre = ctk.CTkLabel(self.visor, text="ESPERANDO ESCANEO...", font=("Arial", 28, "bold"), wraplength=800)
        self.lbl_nombre.pack(pady=2)

        self.lbl_precio = ctk.CTkLabel(self.visor, text="$ 0", font=("Arial", 140, "bold"), text_color="#D4AF37")
        self.lbl_precio.pack(pady=0)

        self.lbl_semaforo = ctk.CTkLabel(self.visor, text="", font=("Arial", 18, "bold"), corner_radius=10, height=40)
        self.lbl_semaforo.pack(pady=4)

        # --- BARRA DE EDICIÓN RÁPIDA ---
        self.edit_frame = ctk.CTkFrame(self.visor, fg_color="transparent")

        ctk.CTkLabel(self.edit_frame, text="NUEVO PRECIO:", font=("Arial", 13, "bold"), text_color="gray").pack(side="left", padx=(0, 6))

        self.entry_nuevo_precio = ctk.CTkEntry(
            self.edit_frame, font=("Arial", 16, "bold"), justify="center", width=180, height=38,
            validate="key", validatecommand=(self._val_precio, "%P")
        )
        self.entry_nuevo_precio.pack(side="left", padx=(0, 8), pady=8)
        self.entry_nuevo_precio.bind("<Return>", lambda e: self.guardar_precio_rapido())

        self.btn_guardar_precio = ctk.CTkButton(
            self.edit_frame, text="💾 GUARDAR", fg_color="#e67e22", hover_color="#d35400",
            width=130, height=38, font=("Arial", 13, "bold"), corner_radius=8,
            command=self.guardar_precio_rapido
        )
        self.btn_guardar_precio.pack(side="left", padx=(0, 10), pady=8)

        self.btn_lapiz = ctk.CTkButton(
            self.edit_frame, text="✏️", fg_color="#555555", hover_color="#777777",
            width=42, height=38, font=("Arial", 15), corner_radius=8,
            command=self.abrir_ventana_edicion
        )
        self.btn_lapiz.pack(side="left", padx=(0, 12), pady=8)

        # 3. Historial — justo debajo del editor de precio, dentro del visor
        self.hist_frame = ctk.CTkFrame(self.visor, fg_color="transparent")

        self.after(200, self._focus_scan)
        self.after(150, lambda: self._escalar_fuentes(self.winfo_width(), self.winfo_height()))

    def _mostrar_btn_registrar_ahora(self, cod):
        # Limpiar si ya había un botón previo
        if hasattr(self, '_btn_reg_ahora') and self._btn_reg_ahora.winfo_exists():
            self._btn_reg_ahora.destroy()
        self._btn_reg_ahora = ctk.CTkButton(
            self.visor, text="➕ REGISTRAR ESTE PRODUCTO",
            fg_color="#2ecc71", hover_color="#27ae60",
            height=50, font=("Arial", 16, "bold"), corner_radius=10,
            command=lambda: self.abrir_ventana_registro(cod)
        )
        self._btn_reg_ahora.pack(pady=10)

    def _ocultar_btn_registrar_ahora(self):
        if hasattr(self, '_btn_reg_ahora') and self._btn_reg_ahora.winfo_exists():
            self._btn_reg_ahora.destroy()

    def _focus_scan(self):
        self.entry_scan.focus_set()
        self.entry_scan.focus_force()

    # --- ESCALADO RESPONSIVO ---

    def _on_resize(self, event=None):
        if event and event.widget == self:
            self._escalar_fuentes(event.width, event.height)

    def _escalar_fuentes(self, w, h):
        escala = min(w / 1024, h / 768)
        escala = max(escala, 0.45)

        t_precio   = max(int(230 * escala), 50)  # +40% sobre 165
        t_nombre   = max(int(34  * escala), 14)
        t_guia     = max(int(18  * escala), 10)
        t_scan     = max(int(42  * escala), 16)
        t_semaf    = max(int(20  * escala), 10)
        t_hist     = max(int(13  * escala), 8)
        ancho_scan = max(int(440 * escala), 180)
        alto_scan  = max(int(70  * escala), 30)
        wrap       = max(int(w * 0.82), 200)

        self.lbl_precio.configure(font=("Arial", t_precio, "bold"))
        self.lbl_nombre.configure(font=("Arial", t_nombre, "bold"), wraplength=wrap)
        self.lbl_guia.configure(font=("Arial", t_guia, "bold"))
        self.entry_scan.configure(font=("Arial", t_scan, "bold"), width=ancho_scan, height=alto_scan)
        self.lbl_semaforo.configure(font=("Arial", t_semaf, "bold"))

        for frame in self.hist_frame.winfo_children():
            for lbl in frame.winfo_children():
                try: lbl.configure(font=("Arial", t_hist, "bold"))
                except: pass

    # --- FUNCIONES DE CONTROL ---

    def _on_focus_principal(self, event=None):
        if event and event.widget == self:
            if self._proteger_emergente:
                return
            self.cerrar_emergente_si_existe()

    def cerrar_emergente_si_existe(self):
        if self._proteger_emergente:
            return
        if self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.destroy()
            self.ventana_abierta = None

    def _abrir_emergente(self, titulo, geometry):
        """Crea y devuelve una ventana emergente con protección anti-cierre."""
        # Forzar cierre de cualquier ventana anterior, ignorando el flag
        if self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.destroy()
            self.ventana_abierta = None
        self._proteger_emergente = True
        v = ctk.CTkToplevel(self)
        v.title(titulo)
        v.geometry(geometry)
        v.transient(self)
        v.lift()
        v.focus_force()
        self.ventana_abierta = v
        self.after(self._tiempo_proteccion, lambda: setattr(self, '_proteger_emergente', False))

        # macOS no dispara FocusIn en la principal — usamos FocusOut en la emergente
        if OS == "Darwin":
            def _on_focusout_emergente(event):
                self.after(150, lambda: self._cerrar_si_foco_en_principal(v))
            v.bind("<FocusOut>", _on_focusout_emergente)

        return v

    def _cerrar_si_foco_en_principal(self, v):
        """Cierra la emergente solo si el foco está ahora en la ventana principal."""
        if self._proteger_emergente:
            return
        try:
            foco = self.focus_get()
            # Si el foco está en la principal o en un widget de ella, cerrar
            if foco and str(foco).startswith(str(self)):
                if self.ventana_abierta and self.ventana_abierta.winfo_exists():
                    self.ventana_abierta.destroy()
                    self.ventana_abierta = None
        except Exception:
            pass

    def confirmar_salida(self):
        if messagebox.askokcancel("Salir", "¿Desea salir de KitoMarket Pro?\n\nCualquier cambio ya se actualizó al servidor."):
            self.destroy()

    def buscar_barras(self, event=None):
        cod = self.entry_scan.get().strip()
        if not cod: return

        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT codigo, nombre, precio, fecha_actualizacion FROM productos WHERE codigo = ?", (cod,))
        res = c.fetchone(); conn.close()

        if res:
            self.codigo_actual = res[0]
            self.lbl_nombre.configure(text=str(res[1]).upper(), text_color=("#111", "#EEE"))
            self.lbl_precio.configure(text=f"${res[2]:,}".replace(",", "."))
            self.gestionar_semaforo(res[3])
            self.actualizar_historial(res[1], res[2])
            self.entry_nuevo_precio.delete(0, 'end')
            self.edit_frame.pack(pady=(4, 0))
            self.hist_frame.pack(pady=(6, 0))
            self._ocultar_btn_registrar_ahora()
        else:
            self.codigo_actual = cod
            self.lbl_nombre.configure(text="ARTÍCULO NO ENCONTRADO", text_color="#e74c3c")
            self.lbl_precio.configure(text="---")
            self.lbl_semaforo.configure(text=f"CÓDIGO: {cod}", fg_color="transparent", text_color="gray")
            self.edit_frame.pack_forget()
            self.hist_frame.pack_forget()
            # Botón para registrar el producto recién escaneado
            self._mostrar_btn_registrar_ahora(cod)

        self.entry_scan.delete(0, 'end')

    def gestionar_semaforo(self, fecha_str):
        if not fecha_str or fecha_str.strip() == "":
            self.lbl_semaforo.configure(text="🚨 SIN FECHA - REVISAR PRECIO", fg_color="#D32F2F", text_color="white")
            return
        try:
            f_dt = datetime.strptime(fecha_str.split()[0], "%d/%m/%Y")
            dias = (datetime.now() - f_dt).days
            if dias < 90:
                self.lbl_semaforo.configure(text=f"✅ PRECIO AL DÍA ({fecha_str})", fg_color="#2E7D32", text_color="white")
            elif dias < 365:
                self.lbl_semaforo.configure(text=f"⚠️ PRECIO ANTIGUO ({fecha_str})", fg_color="#FBC02D", text_color="black")
            else:
                self.lbl_semaforo.configure(text=f"🚨 VERIFICAR URGENTE ({fecha_str})", fg_color="#D32F2F", text_color="white")
        except:
            self.lbl_semaforo.configure(text="🚨 ERROR FECHA", fg_color="#D32F2F", text_color="white")

    def actualizar_historial(self, nom, pre):
        item = (nom[:15].upper(), f"${pre:,}".replace(",", "."))
        self.historial_data = [h for h in self.historial_data if h[0] != item[0]]
        self.historial_data.insert(0, item)
        self.historial_data = self.historial_data[:5]

        for w in self.hist_frame.winfo_children(): w.destroy()
        colores = ["#5D4037", "#455A64", "#512DA8", "#E64A19", "#388E3C"]
        escala = min(self.winfo_width() / 1024, self.winfo_height() / 768)
        t_hist = max(int(13 * escala), 8)
        for i, (n, p) in enumerate(self.historial_data):
            f = ctk.CTkFrame(self.hist_frame, fg_color=colores[i], corner_radius=8)
            f.pack(side="left", padx=8)
            ctk.CTkLabel(f, text=f"{n}\n{p}", font=("Arial", t_hist, "bold"), text_color="white", padx=12, pady=8).pack()

    # --- VENTANAS EMERGENTES ---

    def guardar_precio_rapido(self):
        if not self.codigo_actual: return
        p = self.entry_nuevo_precio.get().strip()
        if not p.isdigit():
            messagebox.showwarning("Precio inválido", "Ingresa solo números.")
            return
        nombre = self.lbl_nombre.cget("text")
        confirmar = messagebox.askyesno(
            "Confirmar cambio",
            f"¿Actualizar precio de:\n\n{nombre}\n\na ${int(p):,}?".replace(",", ".")
        )
        if not confirmar:
            return
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("UPDATE productos SET precio=?, fecha_actualizacion=? WHERE codigo=?",
                    (int(p), datetime.now().strftime("%d/%m/%Y"), self.codigo_actual))
        conn.commit(); conn.close()
        self.entry_scan.insert(0, self.codigo_actual)
        self.buscar_barras()
        self.after(100, self._focus_scan)

    def abrir_ventana_edicion(self):
        if not self.codigo_actual: return
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT nombre, precio FROM productos WHERE codigo=?", (self.codigo_actual,))
        res = c.fetchone(); conn.close()
        if not res: return

        v = self._abrir_emergente("Corregir Producto", "450x360")

        ctk.CTkLabel(v, text="✏️ CORREGIR PRODUCTO", font=("Arial", 20, "bold")).pack(pady=20)
        e_n = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16))
        e_n.insert(0, res[0]); e_n.pack(pady=10)
        e_p = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16),
                           validate="key", validatecommand=(self._val_precio, "%P"))
        e_p.insert(0, str(res[1])); e_p.pack(pady=10)

        def guardar_edicion():
            nom = e_n.get().strip().upper()
            pre = e_p.get().strip()
            if nom and pre.isdigit():
                conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
                cur.execute("UPDATE productos SET nombre=?, precio=?, fecha_actualizacion=? WHERE codigo=?",
                            (nom, int(pre), datetime.now().strftime("%d/%m/%Y"), self.codigo_actual))
                conn.commit(); conn.close()
                v.destroy(); self.ventana_abierta = None
                self.entry_scan.insert(0, self.codigo_actual)
                self.buscar_barras()
                self.after(100, self._focus_scan)
            else:
                messagebox.showwarning("Datos inválidos", "Nombre no puede estar vacío y precio debe ser número.")

        ctk.CTkButton(v, text="GUARDAR CAMBIOS", fg_color="#2ecc71", height=50, width=340, command=guardar_edicion).pack(pady=20)

    def abrir_ventana_registro(self, cod_sugerido=""):
        v = self._abrir_emergente("Registro de Producto", "450x500")

        ctk.CTkLabel(v, text="DATOS DEL PRODUCTO", font=("Arial", 20, "bold")).pack(pady=20)
        e_c = ctk.CTkEntry(v, placeholder_text="Código", width=300, height=40,
                           validate="key", validatecommand=(self._val_num, "%P")); e_c.pack(pady=10)
        if cod_sugerido: e_c.insert(0, str(cod_sugerido))
        e_n = ctk.CTkEntry(v, placeholder_text="Nombre", width=300, height=40); e_n.pack(pady=10)
        e_p = ctk.CTkEntry(v, placeholder_text="Precio (máx. 6 dígitos)", width=300, height=40,
                           validate="key", validatecommand=(self._val_precio, "%P")); e_p.pack(pady=10)

        def guardar():
            c, n, p = e_c.get().strip(), e_n.get().strip().upper(), e_p.get().strip()
            if c and n and p.isdigit():
                conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO productos VALUES (?,?,?,?)", (c, n, int(p), datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); conn.close()
                v.destroy(); self.ventana_abierta = None
                self.entry_scan.insert(0, c); self.buscar_barras()
                self.after(100, self._focus_scan)

        ctk.CTkButton(v, text="GUARDAR", fg_color="#2ecc71", height=50, width=300, command=guardar).pack(pady=20)

    def abrir_ventana_busqueda(self):
        v = self._abrir_emergente("Buscador de Artículos", "550x600")

        e_bus = ctk.CTkEntry(v, placeholder_text="Nombre del producto...", height=45); e_bus.pack(fill="x", padx=30, pady=20)
        import tkinter as tk
        lb = tk.Listbox(v, font=("Arial", 16), bg="#f0f0f0"); lb.pack(fill="both", expand=True, padx=30, pady=10)

        def buscar(ev=None):
            t = e_bus.get().strip(); lb.delete(0, 'end')
            if len(t) < 2: return
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT codigo, nombre, precio FROM productos WHERE nombre LIKE ?", (f'%{t}%',))
            for r in c.fetchall(): lb.insert('end', f" {r[1]} | ${r[2]:,} | ({r[0]})")
            conn.close()

        def seleccionar(ev=None):
            try:
                item = lb.get(lb.curselection())
                cod = item.split("(")[-1].replace(")", "")
                v.destroy(); self.ventana_abierta = None
                self.entry_scan.insert(0, cod); self.buscar_barras()
            except: pass

        e_bus.bind("<KeyRelease>", buscar)
        lb.bind("<Double-Button-1>", seleccionar)

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS productos (codigo TEXT PRIMARY KEY, nombre TEXT, precio INTEGER, fecha_actualizacion TEXT)")
    conn.close()
    app = MinimarketApp()
    app.withdraw()  # ocultar app principal mientras carga
    splash = SplashScreen(app)
    # Después de 2.5s cerrar splash y mostrar app
    def lanzar():
        splash.destroy()
        app.deiconify()
        if OS == "Windows":
            app.state('zoomed')
        elif OS == "Darwin":
            app.state('zoomed')
        else:
            app.attributes('-zoomed', True)
        app.after(200, app._focus_scan)
    app.after(2500, lanzar)
    app.mainloop()
