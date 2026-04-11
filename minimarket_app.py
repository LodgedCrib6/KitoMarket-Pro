import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import os
import sys
import platform
from PIL import Image, ImageTk

OS = platform.system()  # "Windows", "Darwin" (macOS), "Linux"

# --- CONFIGURACIÓN DE RECURSOS (ICONOS) ---
def obtener_ruta_recurso(nombre_archivo):
    """
    Busca un recurso (ícono, imagen) en el orden correcto:
    1. Carpeta de recursos empaquetados (_MEIPASS para PyInstaller)
    2. Directorio del ejecutable (para AppImage)
    3. Directorio del script (desarrollo)
    """
    # Opción 1: PyInstaller (Windows/macOS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        ruta = os.path.join(sys._MEIPASS, nombre_archivo)
        if os.path.exists(ruta):
            return ruta
    
    # Opción 2: Ejecutable empaquetado (AppImage en Linux)
    if getattr(sys, 'frozen', False):
        ruta = os.path.join(os.path.dirname(sys.executable), nombre_archivo)
        if os.path.exists(ruta):
            return ruta
    
    # Opción 3: Desarrollo (mismo directorio del .py)
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)
    if os.path.exists(ruta):
        return ruta
    
    # No encontrado
    return None

# --- CONFIGURACIÓN DE DB ---
def obtener_ruta_db():
    """
    Estrategia inteligente para productos.db:
    1. Intentar usar la carpeta del ejecutable (portabilidad)
    2. Si no tiene permisos de escritura, usar ~/.kitomarket/
    """
    if getattr(sys, 'frozen', False):
        # Aplicación empaquetada
        if "Contents/MacOS" in os.path.dirname(sys.executable):
            # macOS .app bundle
            base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../.."))
        else:
            # Windows .exe o Linux AppImage
            base_path = os.path.dirname(sys.executable)
        
        db_path = os.path.join(base_path, "productos.db")
        
        # Verificar si podemos escribir en esa ubicación
        try:
            # Intentar crear/abrir el archivo para verificar permisos
            test_conn = sqlite3.connect(db_path)
            test_conn.close()
            return db_path
        except (PermissionError, sqlite3.OperationalError):
            # No tenemos permisos - usar carpeta home
            pass
    else:
        # Modo desarrollo
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "productos.db")
    
    # Fallback: carpeta en home del usuario
    base_path = os.path.join(os.path.expanduser("~"), ".kitomarket")
    os.makedirs(base_path, exist_ok=True)
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
            logo_path = obtener_ruta_recurso("KitoLogo.png")
            if logo_path:
                img = Image.open(logo_path).resize((200, 200), Image.LANCZOS)
                self._logo = ImageTk.PhotoImage(img)
                ctk.CTkLabel(self, image=self._logo, text="").pack(pady=(40, 10))
            else:
                raise FileNotFoundError("Logo no encontrado")
        except Exception as e:
            print(f"⚠️ No se pudo cargar el logo: {e}")
            ctk.CTkLabel(self, text="🏪", font=("Arial", 80)).pack(pady=(40, 10))

        ctk.CTkLabel(self, text="KitoMarket Pro", font=("Arial", 22, "bold"), text_color="#2ecc71").pack()
        ctk.CTkLabel(self, text="Cargando...", font=("Arial", 12), text_color="gray").pack(pady=(6, 0))


class MinimarketApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KitoMarket Pro")
        
        # Configurar ícono de la ventana
        try:
            if OS == "Windows":
                ico_path = obtener_ruta_recurso("KitoLogo.ico")
                if ico_path:
                    self.iconbitmap(ico_path)
            elif OS == "Linux":
                png_path = obtener_ruta_recurso("KitoLogo.png")
                if png_path:
                    icon = ImageTk.PhotoImage(Image.open(png_path).resize((64, 64)))
                    self.iconphoto(True, icon)
            # macOS: el ícono lo maneja el .icns del bundle, no hace falta código
        except Exception as e:
            print(f"⚠️ No se pudo configurar el ícono: {e}")
        
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
        if hasattr(self, "btn_reg_ahora"):
            self.btn_reg_ahora.destroy()
        self.btn_reg_ahora = ctk.CTkButton(
            self.visor,
            text=f"➕ REGISTRAR ESTE PRODUCTO ({cod})",
            fg_color="#e74c3c", hover_color="#c0392b",
            width=450, height=60, font=("Arial", 16, "bold"), corner_radius=12,
            command=lambda: self.abrir_ventana_registro(cod)
        )
        self.btn_reg_ahora.pack(pady=20)

    def _ocultar_btn_registrar_ahora(self):
        if hasattr(self, "btn_reg_ahora"):
            self.btn_reg_ahora.destroy()
            del self.btn_reg_ahora

    def _abrir_emergente(self, titulo, size="450x450"):
        if self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.lift()
            return None
        v = ctk.CTkToplevel(self)
        v.title(titulo)
        v.geometry(size)
        v.resizable(False, False)
        v.attributes("-topmost", True)
        v.grab_set()
        self.ventana_abierta = v
        self._proteger_emergente = True
        v.after(self._tiempo_proteccion, lambda: setattr(self, '_proteger_emergente', False))

        if OS == "Windows":
            v.bind("<FocusIn>", lambda e: None)
        else:
            v.bind("<FocusOut>", lambda e: self._verificar_foco_emergente(v))
        return v

    def _verificar_foco_emergente(self, ventana):
        if self._proteger_emergente:
            return
        try:
            if ventana.winfo_exists():
                ventana.destroy()
                self.ventana_abierta = None
        except:
            pass

    def cerrar_emergente_si_existe(self):
        if self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.destroy()
            self.ventana_abierta = None

    def _on_focus_principal(self, event):
        if not self._proteger_emergente and self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.destroy()
            self.ventana_abierta = None

    def _focus_scan(self):
        self.entry_scan.focus_set()

    def _on_resize(self, event):
        if event.widget == self:
            self._escalar_fuentes(event.width, event.height)

    def _escalar_fuentes(self, w, h):
        escala = min(w / 1024, h / 768)
        t_guia = max(int(16 * escala), 10)
        t_scan = max(int(36 * escala), 18)
        t_nom  = max(int(28 * escala), 14)
        t_pre  = max(int(140 * escala), 50)
        t_sem  = max(int(18 * escala), 11)
        t_bot  = max(int(14 * escala), 9)

        self.lbl_guia.configure(font=("Arial", t_guia, "bold"))
        self.entry_scan.configure(font=("Arial", t_scan, "bold"))
        self.lbl_nombre.configure(font=("Arial", t_nom, "bold"))
        self.lbl_precio.configure(font=("Arial", t_pre, "bold"))
        self.lbl_semaforo.configure(font=("Arial", t_sem, "bold"))
        self.btn_reg.configure(font=("Arial", t_bot, "bold"))
        self.btn_bus.configure(font=("Arial", t_bot, "bold"))

    def confirmar_salida(self):
        if messagebox.askokcancel("Salir", "¿Cerrar KitoMarket Pro?"):
            self.destroy()

    def buscar_barras(self, ev=None):
        cod = self.entry_scan.get().strip()
        if not cod: return
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT nombre, precio, fecha_actualizacion FROM productos WHERE codigo=?", (cod,))
        res = c.fetchone(); conn.close()

        if res:
            self.codigo_actual = cod
            self.lbl_nombre.configure(text=res[0], text_color="black")
            self.lbl_precio.configure(text=f"$ {res[1]:,}".replace(",", "."))
            self.gestionar_semaforo(res[2])
            self.actualizar_historial(res[0], res[1])
            self.entry_nuevo_precio.delete(0, 'end')
            self.edit_frame.pack(pady=(10, 0))
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
    # Mostrar ruta de la base de datos en consola (útil para debug)
    print(f"📁 Base de datos: {DB_PATH}")
    
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
