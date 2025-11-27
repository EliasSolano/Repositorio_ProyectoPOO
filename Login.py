from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

class LoginPanel:

    def __init__(self, app_gui, sistema):
        self.app = app_gui
        self.sistema = sistema

        parent = getattr(self.app, "contenido", self.app)
        self.frame = ctk.CTkFrame(parent)

        lbl = ctk.CTkLabel(self.frame, text="Iniciar sesión o registrarse", font=("Arial", 16))
        lbl.pack(pady=10)

        self.entrada_usuario_login = ctk.CTkEntry(self.frame, placeholder_text="Usuario")
        self.entrada_usuario_login.pack(pady=6)
        self.entrada_pass_login = ctk.CTkEntry(self.frame, placeholder_text="Contraseña", show="*")
        self.entrada_pass_login.pack(pady=6)

        btn_login = ctk.CTkButton(self.frame, text="Iniciar sesión", command=self.accion_login)
        btn_register = ctk.CTkButton(self.frame, text="Registrarse", command=self.accion_registrar)
        btn_login.pack(pady=6)
        btn_register.pack(pady=6)

        self.mensaje_login = ctk.CTkLabel(self.frame, text="")
        self.mensaje_login.pack(pady=6)

        if not hasattr(self.app, "etiqueta_usuario"):
            self.app.etiqueta_usuario = ctk.CTkLabel(self.app, text="Sin sesión")
        if not hasattr(self.app, "boton_logout"):
            self.app.boton_logout = ctk.CTkButton(self.app, text="Logout", command=self._logout_local, state="disabled")

    def accion_registrar(self):
        u = self.entrada_usuario_login.get().strip()
        p = self.entrada_pass_login.get().strip()
        if not u or not p:
            self.mensaje_login.configure(text="Usuario/contraseña obligatorios", text_color="red")
            return
        ok = self.sistema.registrar_usuario(u, p)
        if ok:
            self.mensaje_login.configure(text="Usuario creado. Inicia sesión.", text_color="green")
        else:
            self.mensaje_login.configure(text="Usuario ya existe", text_color="red")

    def accion_login(self):
        u = self.entrada_usuario_login.get().strip()
        p = self.entrada_pass_login.get().strip()
        if not u or not p:
            self.mensaje_login.configure(text="Usuario/contraseña obligatorios", text_color="red")
            return
        if self.sistema.verificar_usuario(u, p):
            try:
                self.app.usuario_logueado = u
            except Exception:
                pass
            try:
                self.app.etiqueta_usuario.configure(text=f"Usuario: {u}")
            except Exception:
                pass
            try:
                self.app.boton_logout.configure(state="normal")
            except Exception:
                pass
            self.mensaje_login.configure(text="Inicio correcto", text_color="green")
            self.entrada_usuario_login.delete(0, "end")
            self.entrada_pass_login.delete(0, "end")
            try:
                if hasattr(self.app, "mostrar_cursos"):
                    self.app.mostrar_cursos()
            except Exception:
                pass
        else:
            self.mensaje_login.configure(text="Usuario/contraseña incorrectos", text_color="red")

    def logout(self):
        try:
            self.app.usuario_logueado = None
        except Exception:
            pass
        try:
            self.app.etiqueta_usuario.configure(text="Sin sesión")
        except Exception:
            pass
        try:
            self.app.boton_logout.configure(state="disabled")
        except Exception:
            pass
        messagebox.showinfo("Logout", "Sesión cerrada.")
        try:
            if hasattr(self.app, "mostrar_login"):
                self.app.mostrar_login()
        except Exception:
            pass

    def _logout_local(self):
        self.logout()

if __name__ == "__main__":
    try:
        from asistencia_app import SistemaAsistencia  
    except Exception:
        class SistemaAsistencia:
            def __init__(self):
                self.usuarios = {}
            def registrar_usuario(self, nombre_usuario: str, password: str) -> bool:
                if nombre_usuario in self.usuarios:
                    return False
                uid = max([u["id"] for u in self.usuarios.values()], default=0) + 1
                self.usuarios[nombre_usuario] = {"id": uid, "password": password}
                return True

            def verificar_usuario(self, nombre_usuario: str, password: str) -> bool:
                u = self.usuarios.get(nombre_usuario)
                return bool(u and u.get("password") == password)

    class AppSimulada(ctk.CTk):
        def __init__(self, sistema):
            super().__init__()
            self.sistema = sistema
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.title("Sistema de Asistencia - Login (prueba)")
            self.geometry("600x400")

            header = ctk.CTkFrame(self)
            header.pack(side="top", fill="x", padx=8, pady=6)
            self.etiqueta_titulo = ctk.CTkLabel(header, text="Sistema de Asistencia", font=("Arial", 20))
            self.etiqueta_titulo.pack(side="left", padx=8)
            self.etiqueta_usuario = ctk.CTkLabel(header, text="Sin sesión")
            self.etiqueta_usuario.pack(side="right", padx=8)
            self.boton_logout = ctk.CTkButton(header, text="Logout", command=self._on_logout, state="disabled")
            self.boton_logout.pack(side="right", padx=8)

            self.contenido = ctk.CTkFrame(self)
            self.contenido.pack(fill="both", expand=True, padx=8, pady=6)

        def mostrar_cursos(self):
            messagebox.showinfo("Navegación", "mostrar_cursos() llamado (simulación)")

        def mostrar_login(self):
            for w in self.contenido.winfo_children():
                w.pack_forget()
            login_panel.frame.pack(fill="both", expand=True, padx=12, pady=12)

        def _on_logout(self):
            try:
                login_panel.logout()
            except Exception:
                self.etiqueta_usuario.configure(text="Sin sesión")
                self.boton_logout.configure(state="disabled")

    sistema = SistemaAsistencia()
    app = AppSimulada(sistema)
    login_panel = LoginPanel(app, sistema)
    login_panel.frame.pack(fill="both", expand=True, padx=12, pady=12)
    app.mainloop()
