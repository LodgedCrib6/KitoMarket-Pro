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
        # Caso especial: AppImage en Linux (usa variable APPIMAGE)
        if 'APPIMAGE' in os.environ:
            # APPIMAGE apunta al .AppImage original, no al mount temporal
            base_path = os.path.dirname(os.environ['APPIMAGE'])
        elif "Contents/MacOS" in os.path.dirname(sys.executable):
            base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../.."))
        else:
            base_path = os.path.dirname(sys.executable)
        
        # Verificar permisos de escritura
        db_path = os.path.join(base_path, "productos.db")
        try:
            test_conn = sqlite3.connect(db_path)
            test_conn.close()
            return db_path
        except (PermissionError, sqlite3.OperationalError):
            # Fallback a carpeta home
            base_path = os.path.join(os.path.expanduser("~"), ".kitomarket")
            os.makedirs(base_path, exist_ok=True)
            return os.path.join(base_path, "productos.db")
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
            # En AppImage, usar APPDIR; en desarrollo/PyInstaller, usar _MEIPASS o directorio del script
            if 'APPDIR' in os.environ:
                logo_path = os.path.join(os.environ['APPDIR'], "kitomarket.png")
            elif getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                logo_path = os.path.join(sys._MEIPASS, "KitoLogo256.png" if OS == "Linux" else "KitoLogo.png")
            else:
                logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "KitoLogo256.png" if OS == "Linux" else "KitoLogo.png")
            
            img = Image.open(logo_path).resize((200, 200), Image.LANCZOS)
            self._logo = ImageTk.PhotoImage(img)
            ctk.CTkLabel(self, image=self._logo, text="").pack(pady=(40, 10))
        except Exception as e:
            print(f"⚠️ No se pudo cargar el logo del splash: {e}")
            ctk.CTkLabel(self, text="🏪", font=("Arial", 80)).pack(pady=(40, 10))

        ctk.CTkLabel(self, text="KitoMarket Pro", font=("Arial", 22, "bold"), text_color="#2ecc71").pack()
        ctk.CTkLabel(self, text="Cargando...", font=("Arial", 12), text_color="gray").pack(pady=(6, 0))


class MinimarketApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KitoMarket Pro")
        try:
            if OS == "Windows":
                base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                self.iconbitmap(os.path.join(base, "KitoLogo.ico"))
            elif OS == "Linux":
                # En AppImage, usar APPDIR; en desarrollo, usar directorio del script
                if 'APPDIR' in os.environ:
                    icon_path = os.path.join(os.environ['APPDIR'], "kitomarket.png")
                elif getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    icon_path = os.path.join(sys._MEIPASS, "KitoLogo256.png")
                else:
                    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "KitoLogo256.png")
                
                icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.iconphoto(True, icon)
            # macOS: el ícono lo maneja el .icns del bundle, no hace falta código
        except Exception as e:
            print(f"⚠️ No se pudo configurar el ícono de la ventana: {e}")
        self.ventana_abierta = None
        self.codigo_actual = None
        self.historial_data = []
        self._proteger_emergente = False
        self._tiempo_proteccion = 500 if OS == "Windows" else 200

        # --- Colores de fondo (normal vs. alerta roja) ---
        self._bg_normal = "#EBEBEB"
        self._bg_alerta = "#EF9A8E"
        self.configure(fg_color=self._bg_normal)

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

        self.btn_calc = ctk.CTkButton(self.top_bar, text="🧮 CALCULADORA", fg_color="#8e44ad", hover_color="#6c3483", width=170, height=45, font=("Arial", 14, "bold"), command=self.abrir_modo_calculadora)
        self.btn_calc.pack(side="left", expand=True)

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

        self.lbl_codigo = ctk.CTkLabel(self.visor, text="", font=("Arial", 13), text_color="gray")
        self.lbl_codigo.pack(pady=(0, 2))

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

        self.btn_confirmar_precio = ctk.CTkButton(
            self.edit_frame, text="✅ CONFIRMAR PRECIO", fg_color="#2E7D32", hover_color="#1B5E20",
            width=170, height=38, font=("Arial", 13, "bold"), corner_radius=8,
            command=self.confirmar_precio_actual
        )
        self.btn_confirmar_precio.pack(side="left", padx=(0, 10), pady=8)

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
        t_codigo   = max(int(13  * escala), 9)
        t_hist     = max(int(13  * escala), 8)
        ancho_scan = max(int(440 * escala), 180)
        alto_scan  = max(int(70  * escala), 30)
        wrap       = max(int(w * 0.82), 200)

        self.lbl_precio.configure(font=("Arial", t_precio, "bold"))
        self.lbl_nombre.configure(font=("Arial", t_nombre, "bold"), wraplength=wrap)
        self.lbl_guia.configure(font=("Arial", t_guia, "bold"))
        self.entry_scan.configure(font=("Arial", t_scan, "bold"), width=ancho_scan, height=alto_scan)
        self.lbl_semaforo.configure(font=("Arial", t_semaf, "bold"))
        self.lbl_codigo.configure(font=("Arial", t_codigo))

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
            # Verificar si la ventana emergente sigue existiendo
            if not (self.ventana_abierta and self.ventana_abierta.winfo_exists()):
                return
            
            foco = self.focus_get()
            # Si no hay foco, no hacer nada
            if not foco:
                return
            
            # Verificar si el foco está en la ventana emergente
            foco_en_emergente = False
            widget_actual = foco
            while widget_actual:
                if widget_actual == v:
                    foco_en_emergente = True
                    break
                try:
                    widget_actual = widget_actual.master
                except:
                    break
            
            # Solo cerrar si el foco NO está en la emergente
            if not foco_en_emergente:
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
            self.lbl_codigo.configure(text=f"Código: {res[0]}")
            self.gestionar_semaforo(res[3])
            self.actualizar_historial(res[1], res[2])
            self.entry_nuevo_precio.delete(0, 'end')
            self.edit_frame.pack(pady=(4, 0))
            self.hist_frame.pack(pady=(6, 0))
            self._ocultar_btn_registrar_ahora()
        else:
            self.codigo_actual = cod
            self.lbl_nombre.configure(text="ARTÍCULO NO ENCONTRADO", text_color="#B71C1C")
            self.lbl_precio.configure(text="---")
            self.lbl_codigo.configure(text=f"Código: {cod}")
            self.lbl_semaforo.configure(text="", fg_color="transparent")
            self.edit_frame.pack_forget()
            self.hist_frame.pack_forget()
            self._set_fondo_alerta(True)
            # Botón para registrar el producto recién escaneado
            self._mostrar_btn_registrar_ahora(cod)

        self.entry_scan.delete(0, 'end')

    def _set_fondo_alerta(self, activo):
        """Tiñe toda la ventana de un rojo suave cuando el precio está muy desactualizado o el producto no existe."""
        self.configure(fg_color=self._bg_alerta if activo else self._bg_normal)

    def _nivel_alerta_precio(self, fecha_str):
        """Devuelve 'rojo', 'amarillo' o 'verde' según la antigüedad del precio. Se usa también en la calculadora."""
        if not fecha_str or fecha_str.strip() == "":
            return 'rojo'
        try:
            f_dt = datetime.strptime(fecha_str.split()[0], "%d/%m/%Y")
            dias = (datetime.now() - f_dt).days
            if dias < 90:
                return 'verde'
            elif dias < 365:
                return 'amarillo'
            else:
                return 'rojo'
        except:
            return 'rojo'

    def gestionar_semaforo(self, fecha_str):
        if not fecha_str or fecha_str.strip() == "":
            self.lbl_semaforo.configure(text="🚨 SIN FECHA - REVISAR PRECIO", fg_color="#D32F2F", text_color="white")
            self._set_fondo_alerta(True)
            return
        try:
            f_dt = datetime.strptime(fecha_str.split()[0], "%d/%m/%Y")
            dias = (datetime.now() - f_dt).days
            if dias < 90:
                self.lbl_semaforo.configure(text=f"✅ PRECIO AL DÍA ({fecha_str})", fg_color="#2E7D32", text_color="white")
                self._set_fondo_alerta(False)
            elif dias < 365:
                self.lbl_semaforo.configure(text=f"⚠️ PRECIO ANTIGUO ({fecha_str})", fg_color="#FBC02D", text_color="black")
                self._set_fondo_alerta(False)
            else:
                self.lbl_semaforo.configure(text=f"🚨 VERIFICAR URGENTE ({fecha_str})", fg_color="#D32F2F", text_color="white")
                self._set_fondo_alerta(True)
        except:
            self.lbl_semaforo.configure(text="🚨 ERROR FECHA", fg_color="#D32F2F", text_color="white")
            self._set_fondo_alerta(True)

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

    def confirmar_precio_actual(self):
        """Confirma que el precio sigue vigente: solo actualiza la fecha, sin modificar el valor."""
        if not self.codigo_actual: return
        nombre = self.lbl_nombre.cget("text")
        precio_txt = self.lbl_precio.cget("text")
        confirmar = messagebox.askyesno(
            "Confirmar precio",
            f"¿Confirmas que el precio de:\n\n{nombre}\n\nsigue siendo {precio_txt}?\n\n"
            "Esto marca el precio como revisado hoy, sin cambiar su valor."
        )
        if not confirmar:
            return
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("UPDATE productos SET fecha_actualizacion=? WHERE codigo=?",
                    (datetime.now().strftime("%d/%m/%Y"), self.codigo_actual))
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

        v = self._abrir_emergente("Corregir Producto", "450x440")

        ctk.CTkLabel(v, text="✏️ CORREGIR PRODUCTO", font=("Arial", 20, "bold")).pack(pady=(20, 15))

        ctk.CTkLabel(v, text="Nombre del producto", font=("Arial", 13, "bold"), text_color="gray",
                     anchor="w").pack(fill="x", padx=55)
        e_n = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16))
        e_n.insert(0, res[0]); e_n.pack(pady=(2, 12))

        ctk.CTkLabel(v, text="Precio de venta", font=("Arial", 13, "bold"), text_color="gray",
                     anchor="w").pack(fill="x", padx=55)
        e_p = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16),
                           validate="key", validatecommand=(self._val_precio, "%P"))
        e_p.configure(validate="none")
        e_p.insert(0, f"$ {res[1]:,}".replace(",", "."))
        e_p.configure(validate="key")
        e_p.pack(pady=(2, 10))

        def formatear_precio_edicion(event=None):
            crudo = e_p.get().replace("$", "").replace(".", "").replace(" ", "").strip()
            if not crudo.isdigit():
                return
            visual = f"$ {int(crudo):,}".replace(",", ".")
            e_p.configure(validate="none")
            e_p.delete(0, 'end')
            e_p.insert(0, visual)
            e_p.configure(validate="key")
        e_p.bind("<FocusOut>", formatear_precio_edicion)

        def guardar_edicion():
            nom = e_n.get().strip().upper()
            pre = e_p.get().replace("$", "").replace(".", "").replace(" ", "").strip()
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
        v = self._abrir_emergente("Registro de Producto", "450x560")

        ctk.CTkLabel(v, text="DATOS DEL PRODUCTO", font=("Arial", 20, "bold")).pack(pady=(20, 15))

        # --- Código ---
        ctk.CTkLabel(v, text="Código de barras", font=("Arial", 13, "bold"), text_color="gray",
                     anchor="w").pack(fill="x", padx=75)
        e_c = ctk.CTkEntry(v, placeholder_text="Ej: 7801234567890", width=300, height=40,
                           validate="key", validatecommand=(self._val_num, "%P")); e_c.pack(pady=(2, 12))
        if cod_sugerido: e_c.insert(0, str(cod_sugerido))

        # --- Nombre ---
        ctk.CTkLabel(v, text="Nombre del producto", font=("Arial", 13, "bold"), text_color="gray",
                     anchor="w").pack(fill="x", padx=75)
        e_n = ctk.CTkEntry(v, placeholder_text="Ej: COCA COLA 1.5L", width=300, height=40); e_n.pack(pady=(2, 12))

        # --- Precio ---
        ctk.CTkLabel(v, text="Precio de venta", font=("Arial", 13, "bold"), text_color="gray",
                     anchor="w").pack(fill="x", padx=75)
        e_p = ctk.CTkEntry(v, placeholder_text="Ej: 1000", width=300, height=40,
                           validate="key", validatecommand=(self._val_precio, "%P")); e_p.pack(pady=(2, 10))

        # Formatea el precio como $ 1.000 solo al salir del campo.
        # Se desactiva el validador un instante porque el texto formateado ($, espacio, puntos)
        # no son dígitos puros y el validador los rechazaría, dejando el campo vacío.
        def formatear_precio(event=None):
            crudo = e_p.get().replace("$", "").replace(".", "").replace(" ", "").strip()
            if not crudo.isdigit():
                return
            visual = f"$ {int(crudo):,}".replace(",", ".")
            e_p.configure(validate="none")
            e_p.delete(0, 'end')
            e_p.insert(0, visual)
            e_p.configure(validate="key")
        e_p.bind("<FocusOut>", formatear_precio)

        def guardar():
            c = e_c.get().strip()
            n = e_n.get().strip().upper()
            p = e_p.get().replace("$", "").replace(".", "").replace(" ", "").strip()
            if not c or not n or not p.isdigit():
                messagebox.showwarning("Datos incompletos", "Completa código, nombre y un precio válido.")
                return
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

    def abrir_modo_calculadora(self):
        v = self._abrir_emergente("Modo Calculadora", "580x720")
        self._calc_items = []  # cada apertura empieza una cuenta nueva

        ctk.CTkLabel(v, text="🧮 MODO CALCULADORA", font=("Arial", 20, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(v, text="Escanea los productos para ir sumando", font=("Arial", 12), text_color="gray").pack(pady=(0, 10))

        entry_calc = ctk.CTkEntry(v, font=("Arial", 22, "bold"), justify="center", width=300, height=48,
                                   validate="key", validatecommand=(self._val_num, "%P"))
        entry_calc.pack(pady=(0, 12))

        lista_frame = ctk.CTkScrollableFrame(v, width=500, height=260, fg_color="#f0f0f0")
        lista_frame.pack(padx=20, pady=(0, 10), fill="both", expand=True)

        lbl_total = ctk.CTkLabel(v, text="TOTAL: $ 0", font=("Arial", 32, "bold"), text_color="#2E7D32")
        lbl_total.pack(pady=(4, 12))

        # Colores de fila según el nivel de alerta del precio (mismo criterio que la pantalla principal)
        COLOR_FILA = {'rojo': "#F5C6CB", 'amarillo': "#FFF3CD", 'verde': "white", None: "white"}
        ICONO_FILA = {'rojo': "🚨 ", 'amarillo': "⚠️ ", 'verde': "", None: ""}

        def recalcular():
            total = sum(it['precio'] * it['cantidad'] for it in self._calc_items)
            lbl_total.configure(text=f"TOTAL: ${total:,}".replace(",", "."))
            for w in lista_frame.winfo_children(): w.destroy()
            for idx, it in enumerate(self._calc_items):
                subt = it['precio'] * it['cantidad']
                nivel = it.get('nivel')
                fila = ctk.CTkFrame(lista_frame, fg_color=COLOR_FILA.get(nivel, "white"), corner_radius=6)
                fila.pack(fill="x", pady=3, padx=2)
                texto = f"{ICONO_FILA.get(nivel, '')}{it['nombre'][:24]}  x{it['cantidad']}  ·  ${it['precio']:,}".replace(",", ".")
                ctk.CTkLabel(fila, text=texto, font=("Arial", 13), anchor="w", text_color="#111").pack(side="left", padx=10, pady=8, fill="x", expand=True)
                ctk.CTkLabel(fila, text=f"${subt:,}".replace(",", "."), font=("Arial", 13, "bold"), text_color="#111").pack(side="left", padx=8)
                ctk.CTkButton(fila, text="✕", width=30, height=28, fg_color="#c0392b", hover_color="#922b21",
                              command=lambda i=idx: quitar_item(i)).pack(side="right", padx=8)

        def quitar_item(i):
            if 0 <= i < len(self._calc_items):
                self._calc_items.pop(i)
                recalcular()

        def agregar_item(nombre, precio, nivel=None):
            for it in self._calc_items:
                if it['nombre'] == nombre and it['precio'] == precio:
                    it['cantidad'] += 1
                    recalcular()
                    return
            self._calc_items.append({'nombre': nombre, 'precio': precio, 'cantidad': 1, 'nivel': nivel})
            recalcular()

        def procesar_scan(event=None):
            cod = entry_calc.get().strip()
            entry_calc.delete(0, 'end')
            if not cod: return
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT nombre, precio, fecha_actualizacion FROM productos WHERE codigo=?", (cod,))
            res = c.fetchone(); conn.close()
            if res:
                nivel = self._nivel_alerta_precio(res[2])
                agregar_item(res[0], res[1], nivel)
            else:
                messagebox.showwarning("No encontrado", f"El código {cod} no está registrado.\nPuedes agregarlo en 'Otros productos' abajo.")
        entry_calc.bind("<Return>", procesar_scan)

        # --- Otros productos (sin código, no se persiste ni se imprime comprobante) ---
        ctk.CTkLabel(v, text="Otros productos (sin código):", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0, 4))
        frame_manual = ctk.CTkFrame(v, fg_color="transparent")
        frame_manual.pack(pady=(0, 15))

        e_precio_manual = ctk.CTkEntry(frame_manual, placeholder_text="Precio", width=150, height=38,
                                        validate="key", validatecommand=(self._val_precio, "%P"))
        e_precio_manual.pack(side="left", padx=4)

        def agregar_manual():
            pre = e_precio_manual.get().strip()
            if not pre.isdigit():
                messagebox.showwarning("Precio inválido", "Ingresa un precio válido.")
                return
            agregar_item("OTROS PRODUCTOS", int(pre), None)
            e_precio_manual.delete(0, 'end')
            entry_calc.focus_set()
        e_precio_manual.bind("<Return>", lambda e: agregar_manual())

        ctk.CTkButton(frame_manual, text="+ AGREGAR", fg_color="#e67e22", hover_color="#d35400",
                      width=100, height=38, command=agregar_manual).pack(side="left", padx=4)

        ctk.CTkButton(v, text="🗑️ LIMPIAR TODO", fg_color="#c0392b", hover_color="#922b21",
                      width=200, height=42, command=lambda: (self._calc_items.clear(), recalcular())).pack(pady=(0, 15))

        entry_calc.focus_set()

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
