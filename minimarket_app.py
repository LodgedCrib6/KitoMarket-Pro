import customtkinter as ctk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import os
import sys

# --- CONFIGURACIÓN DE DB ---
def obtener_ruta_db():
    if getattr(sys, 'frozen', False):
        ruta_exe = os.path.dirname(sys.executable)
        base_path = os.path.abspath(os.path.join(ruta_exe, "../../..")) if "Contents/MacOS" in ruta_exe else ruta_exe
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "productos.db")

DB_PATH = obtener_ruta_db()

class MinimarketApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KitoMarket Pro")
        # Ícono compatible con PyInstaller --onefile
        try:
            base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            self.iconbitmap(os.path.join(base, "KitoLogo.ico"))
        except Exception:
            pass
        self.ventana_abierta = None
        self.codigo_actual = None
        self.historial_data = []

        # --- Arrancar centrado y adaptado a la pantalla actual ---
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(sw, 1100)
        h = min(sh, 850)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(600, 450)
        self.resizable(True, True)

        self.protocol("WM_DELETE_WINDOW", self.confirmar_salida)
        self.bind("<FocusIn>", self._on_focus_principal)
        self.bind("<Button-1>", self._on_click_principal)  # ← Windows necesita esto
        self.bind("<Configure>", self._on_resize)  # escucha cambios de tamaño

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
        self.lbl_guia.pack(pady=(8, 0))

        self.entry_scan = ctk.CTkEntry(self.visor, font=("Arial", 36, "bold"), justify="center", width=400, height=65)
        self.entry_scan.pack(pady=10)
        self.entry_scan.bind("<Return>", self.buscar_barras)

        self.lbl_nombre = ctk.CTkLabel(self.visor, text="ESPERANDO ESCANEO...", font=("Arial", 28, "bold"), wraplength=800)
        self.lbl_nombre.pack(pady=4)

        self.lbl_precio = ctk.CTkLabel(self.visor, text="$ 0", font=("Arial", 120, "bold"), text_color="#D4AF37")
        self.lbl_precio.pack(pady=0)

        self.lbl_semaforo = ctk.CTkLabel(self.visor, text="", font=("Arial", 18, "bold"), corner_radius=10, height=40)
        self.lbl_semaforo.pack(pady=8)

        # --- BARRA DE EDICIÓN RÁPIDA (oculta hasta que se escanea un producto) ---
        self.edit_frame = ctk.CTkFrame(self.visor, fg_color="transparent")
        # No se hace pack aquí — aparece solo al escanear

        self.entry_nuevo_precio = ctk.CTkEntry(
            self.edit_frame, placeholder_text="Nuevo precio...",
            font=("Arial", 16, "bold"), justify="center", width=200, height=40
        )
        self.entry_nuevo_precio.pack(side="left", padx=(0, 8))
        self.entry_nuevo_precio.bind("<Return>", lambda e: self.guardar_precio_rapido())

        self.btn_guardar_precio = ctk.CTkButton(
            self.edit_frame, text="💾 GUARDAR", fg_color="#e67e22",
            width=120, height=40, font=("Arial", 12, "bold"),
            command=self.guardar_precio_rapido
        )
        self.btn_guardar_precio.pack(side="left", padx=(0, 12))

        self.btn_lapiz = ctk.CTkButton(
            self.edit_frame, text="✏️", fg_color="#7f8c8d",
            width=40, height=40, font=("Arial", 16),
            command=self.abrir_ventana_edicion
        )
        self.btn_lapiz.pack(side="left")

        # 3. Historial Inferior
        self.hist_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.hist_frame.pack(side="bottom", pady=15)

        self.after(100, lambda: self.entry_scan.focus_set())
        self.after(150, lambda: self._escalar_fuentes(self.winfo_width(), self.winfo_height()))

    # --- ESCALADO RESPONSIVO ---

    def _on_resize(self, event=None):
        if event and event.widget == self:
            self._escalar_fuentes(event.width, event.height)

    def _escalar_fuentes(self, w, h):
        # Base de referencia: 1024x768
        escala = min(w / 1024, h / 768)
        escala = max(escala, 0.45)  # mínimo para no quedar ilegible

        t_precio  = max(int(150 * escala), 40)
        t_nombre  = max(int(34  * escala), 14)
        t_guia    = max(int(18  * escala), 10)
        t_scan    = max(int(42  * escala), 16)
        t_semaf   = max(int(20  * escala), 10)
        t_hist    = max(int(13  * escala), 8)
        ancho_scan = max(int(440 * escala), 180)
        alto_scan  = max(int(70  * escala), 30)
        wrap       = max(int(w * 0.82), 200)

        self.lbl_precio.configure(font=("Arial", t_precio, "bold"))
        self.lbl_nombre.configure(font=("Arial", t_nombre, "bold"), wraplength=wrap)
        self.lbl_guia.configure(font=("Arial", t_guia, "bold"))
        self.entry_scan.configure(font=("Arial", t_scan, "bold"), width=ancho_scan, height=alto_scan)
        self.lbl_semaforo.configure(font=("Arial", t_semaf, "bold"))

        # Historial
        for frame in self.hist_frame.winfo_children():
            for lbl in frame.winfo_children():
                try: lbl.configure(font=("Arial", t_hist, "bold"))
                except: pass

    # --- FUNCIONES DE CONTROL ---

    def _on_focus_principal(self, event=None):
        if event and event.widget == self:
            self.cerrar_emergente_si_existe()

    def _on_click_principal(self, event=None):
        # En Windows el FocusIn no siempre dispara, este sí
        # No cerrar si el clic fue en un botón
        if event and isinstance(event.widget, ctk.CTkButton):
            return
        self.cerrar_emergente_si_existe()

    def cerrar_emergente_si_existe(self):
        if self.ventana_abierta and self.ventana_abierta.winfo_exists():
            self.ventana_abierta.destroy()
            self.ventana_abierta = None

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
        else:
            self.codigo_actual = cod
            self.lbl_nombre.configure(text="ARTÍCULO NO ENCONTRADO", text_color="#e74c3c")
            self.lbl_precio.configure(text="---")
            self.lbl_semaforo.configure(text=f"CÓDIGO: {cod}", fg_color="transparent", text_color="gray")
            self.edit_frame.pack_forget()

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
        escala = min(self.winfo_width() / 1100, self.winfo_height() / 850)
        t_hist = max(int(12 * escala), 8)
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
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("UPDATE productos SET precio=?, fecha_actualizacion=? WHERE codigo=?",
                    (int(p), datetime.now().strftime("%d/%m/%Y"), self.codigo_actual))
        conn.commit(); conn.close()
        self.entry_scan.insert(0, self.codigo_actual)
        self.buscar_barras()

    def abrir_ventana_edicion(self):
        if not self.codigo_actual: return
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT nombre, precio FROM productos WHERE codigo=?", (self.codigo_actual,))
        res = c.fetchone(); conn.close()
        if not res: return

        self.cerrar_emergente_si_existe()
        v = ctk.CTkToplevel(self)
        v.title("Corregir Producto")
        v.geometry("450x360")
        v.transient(self)
        v.lift()
        v.focus_force()
        self.ventana_abierta = v

        ctk.CTkLabel(v, text="✏️ CORREGIR PRODUCTO", font=("Arial", 20, "bold")).pack(pady=20)
        e_n = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16))
        e_n.insert(0, res[0]); e_n.pack(pady=10)
        e_p = ctk.CTkEntry(v, width=340, height=45, font=("Arial", 16))
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
            else:
                messagebox.showwarning("Datos inválidos", "Nombre no puede estar vacío y precio debe ser número.")

        ctk.CTkButton(v, text="GUARDAR CAMBIOS", fg_color="#2ecc71", height=50, width=340, command=guardar_edicion).pack(pady=20)

    def abrir_ventana_registro(self, cod_sugerido=""):
        self.cerrar_emergente_si_existe()
        v = ctk.CTkToplevel(self)
        v.title("Registro de Producto")
        v.geometry("450x500")
        v.transient(self)
        v.lift()
        v.focus_force()
        self.ventana_abierta = v

        ctk.CTkLabel(v, text="DATOS DEL PRODUCTO", font=("Arial", 20, "bold")).pack(pady=20)
        e_c = ctk.CTkEntry(v, placeholder_text="Código", width=300, height=40); e_c.pack(pady=10)
        if cod_sugerido: e_c.insert(0, str(cod_sugerido))
        e_n = ctk.CTkEntry(v, placeholder_text="Nombre", width=300, height=40); e_n.pack(pady=10)
        e_p = ctk.CTkEntry(v, placeholder_text="Precio", width=300, height=40); e_p.pack(pady=10)

        def guardar():
            c, n, p = e_c.get().strip(), e_n.get().strip().upper(), e_p.get().strip()
            if c and n and p.isdigit():
                conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO productos VALUES (?,?,?,?)", (c, n, int(p), datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); conn.close()
                v.destroy(); self.ventana_abierta = None
                self.entry_scan.insert(0, c); self.buscar_barras()

        ctk.CTkButton(v, text="GUARDAR", fg_color="#2ecc71", height=50, width=300, command=guardar).pack(pady=20)

    def abrir_ventana_busqueda(self):
        self.cerrar_emergente_si_existe()
        v = ctk.CTkToplevel(self)
        v.title("Buscador de Artículos")
        v.geometry("550x600")
        v.transient(self)
        v.lift()
        v.focus_force()
        self.ventana_abierta = v

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
    app.mainloop()
