from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

class CursosPanel:

    def __init__(self, app_gui, sistema):
        self.app = app_gui
        self.sistema = sistema

        parent = getattr(self.app, "contenido", self.app)
        self.frame = ctk.CTkFrame(parent)

        top = ctk.CTkFrame(self.frame)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Crear / Modificar Cursos", font=("Arial", 14)).pack(side="left", padx=6)

        campos = ctk.CTkFrame(self.frame)
        campos.pack(side="top", fill="x", padx=6, pady=6)
        self.entrada_codigo_curso = ctk.CTkEntry(campos, placeholder_text="Código (ej: CS101)")
        self.entrada_nombre_curso = ctk.CTkEntry(campos, placeholder_text="Nombre del curso")
        self.entrada_horario_curso = ctk.CTkEntry(campos, placeholder_text="Horario (opcional)")
        for w in (self.entrada_codigo_curso, self.entrada_nombre_curso, self.entrada_horario_curso):
            w.pack(padx=4, pady=4)

        btns = ctk.CTkFrame(campos)
        btns.pack(pady=6)
        ctk.CTkButton(btns, text="Crear", command=self.ui_crear_curso).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Editar seleccionado", command=self.ui_editar_curso).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Borrar seleccionado", command=self.ui_eliminar_curso).pack(side="left", padx=6)

        listf = ctk.CTkFrame(self.frame)
        listf.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox_cursos = tk.Listbox(listf, height=14)
        self.listbox_cursos.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(listf, command=self.listbox_cursos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_cursos.config(yscrollcommand=sb.set)
        self.listbox_cursos.bind("<<ListboxSelect>>", self._on_select)

        self.refrescar_lista_cursos()

    def refrescar_lista_cursos(self):
        """Refresca la lista de cursos desde self.sistema.cursos"""
        self.listbox_cursos.delete(0, "end")
        try:
            items = sorted(self.sistema.cursos.items())
        except Exception:
            items = []
        for codigo, c in items:
            nombre = getattr(c, "nombre", str(c))
            horario = getattr(c, "horario", "")
            self.listbox_cursos.insert("end", f"{codigo} - {nombre} ({horario})")

    def ui_crear_curso(self):
        """Crea un curso usando los valores del formulario"""
        codigo = self.entrada_codigo_curso.get().strip()
        nombre = self.entrada_nombre_curso.get().strip()
        horario = self.entrada_horario_curso.get().strip()
        if not codigo or not nombre:
            messagebox.showwarning("Faltan datos", "Código y nombre obligatorios.")
            return
        try:
            self.sistema.crear_curso(codigo, nombre, horario)
            messagebox.showinfo("Éxito", "Curso creado.")
            self.entrada_codigo_curso.delete(0, "end")
            self.entrada_nombre_curso.delete(0, "end")
            self.entrada_horario_curso.delete(0, "end")
            self.refrescar_lista_cursos()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_curso(self):
        sel = self.listbox_cursos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un curso para editar.")
            return
        old_txt = self.listbox_cursos.get(sel[0])
        codigo_antiguo = old_txt.split(" - ")[0]
        codigo_nuevo = self.entrada_codigo_curso.get().strip()
        nuevo_nombre = self.entrada_nombre_curso.get().strip()
        nuevo_horario = self.entrada_horario_curso.get().strip()
        if not codigo_nuevo or not nuevo_nombre:
            messagebox.showwarning("Faltan datos", "Código y nombre obligatorios.")
            return
        try:
            self.sistema.actualizar_curso(codigo_antiguo, codigo_nuevo, nuevo_nombre, nuevo_horario)
            messagebox.showinfo("Éxito", "Curso modificado.")
            self.entrada_codigo_curso.delete(0, "end")
            self.entrada_nombre_curso.delete(0, "end")
            self.entrada_horario_curso.delete(0, "end")
            self.refrescar_lista_cursos()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_curso(self):
        """Elimina el curso seleccionado tras pedir confirmación"""
        sel = self.listbox_cursos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un curso para eliminar.")
            return
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        if messagebox.askyesno("Confirmar", f"Eliminar curso {codigo}? Se borrarán sus sesiones."):
            try:
                self.sistema.eliminar_curso(codigo)
                messagebox.showinfo("Éxito", "Curso eliminado.")
                self.refrescar_lista_cursos()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_select(self, event=None):
        sel = self.listbox_cursos.curselection()
        if not sel:
            return
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        c = self.sistema.cursos.get(codigo)
        if not c:
            return
        try:
            self.entrada_codigo_curso.delete(0, "end")
            self.entrada_codigo_curso.insert(0, c.codigo)
            self.entrada_nombre_curso.delete(0, "end")
            self.entrada_nombre_curso.insert(0, c.nombre)
            self.entrada_horario_curso.delete(0, "end")
            self.entrada_horario_curso.insert(0, c.horario)
        except Exception:
            pass
if __name__ == "__main__":
    try:
        from asistencia_app import SistemaAsistencia  
    except Exception:
        class Curso:
            def __init__(self, codigo, nombre, horario=""):
                self.codigo = codigo
                self.nombre = nombre
                self.horario = horario

        class SistemaAsistencia:
            def __init__(self):
                self.cursos = {}
            def crear_curso(self, codigo, nombre, horario=""):
                if codigo in self.cursos:
                    raise ValueError("Código de curso ya existe")
                c = Curso(codigo, nombre, horario)
                self.cursos[codigo] = c
                return c
            def actualizar_curso(self, codigo_antiguo, codigo_nuevo, nombre, horario):
                if codigo_antiguo not in self.cursos:
                    raise ValueError("Curso no encontrado")
                if codigo_nuevo != codigo_antiguo and codigo_nuevo in self.cursos:
                    raise ValueError("Nuevo código ya existe")
                co = self.cursos.pop(codigo_antiguo)
                co.codigo = codigo_nuevo
                co.nombre = nombre
                co.horario = horario
                self.cursos[codigo_nuevo] = co
                return co
            def eliminar_curso(self, codigo):
                if codigo not in self.cursos:
                    raise ValueError("Curso no encontrado")
                del self.cursos[codigo]

    class AppSimulada(ctk.CTk):
        def __init__(self, sistema):
            super().__init__()
            self.sistema = sistema
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.title("Simulación AppGUI - Cursos")
            self.geometry("800x500")

            header = ctk.CTkFrame(self)
            header.pack(side="top", fill="x", padx=8, pady=6)
            self.etiqueta_titulo = ctk.CTkLabel(header, text="Sistema de Asistencia", font=("Arial", 20))
            self.etiqueta_titulo.pack(side="left", padx=8)
            self.etiqueta_usuario = ctk.CTkLabel(header, text="Sin sesión")
            self.etiqueta_usuario.pack(side="right", padx=8)
            self.boton_logout = ctk.CTkButton(header, text="Logout", state="disabled")
            self.boton_logout.pack(side="right", padx=8)

            self.contenido = ctk.CTkFrame(self)
            self.contenido.pack(fill="both", expand=True, padx=8, pady=6)

    sistema = SistemaAsistencia()
    app = AppSimulada(sistema)
    panel = CursosPanel(app, sistema)
    panel.frame.pack(fill="both", expand=True, padx=12, pady=12)
    app.mainloop()
