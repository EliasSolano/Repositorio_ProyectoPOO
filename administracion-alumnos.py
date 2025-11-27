from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk

class AlumnosPanel:

    def __init__(self, app_gui, sistema):
        self.app = app_gui
        self.sistema = sistema

        parent = getattr(self.app, "contenido", self.app)
        self.frame = ctk.CTkFrame(parent)

        top = ctk.CTkFrame(self.frame)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Alumnos (globales)", font=("Arial", 14)).pack(side="left", padx=6)

        campos = ctk.CTkFrame(self.frame)
        campos.pack(side="top", fill="x", padx=6, pady=6)
        self.entrada_nombre_alumno = ctk.CTkEntry(campos, placeholder_text="Nombre alumno")
        self.entrada_rut_alumno = ctk.CTkEntry(campos, placeholder_text="RUT (opcional)")
        self.entrada_nombre_alumno.pack(padx=4, pady=4)
        self.entrada_rut_alumno.pack(padx=4, pady=4)

        btns = ctk.CTkFrame(campos)
        btns.pack(pady=6)
        ctk.CTkButton(btns, text="Agregar (global)", command=self.ui_agregar_alumno).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Editar seleccionado", command=self.ui_editar_alumno).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Eliminar seleccionado", command=self.ui_eliminar_alumno).pack(side="left", padx=6)

        listf = ctk.CTkFrame(self.frame)
        listf.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox_alumnos = tk.Listbox(listf, height=16)
        self.listbox_alumnos.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(listf, command=self.listbox_alumnos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_alumnos.config(yscrollcommand=sb.set)
        self.listbox_alumnos.bind("<<ListboxSelect>>", self._on_select)

        self.refrescar_lista_alumnos()

    def refrescar_lista_alumnos(self):
        """Refresca la lista de alumnos desde self.sistema.estudiantes"""
        self.listbox_alumnos.delete(0, "end")
        try:
            items = sorted(self.sistema.estudiantes.items())
        except Exception:
            items = []
        for sid, st in items:
            # mostrar en el mismo formato que el original
            nombre = getattr(st, "nombre", str(st))
            rut = getattr(st, "rut", "")
            self.listbox_alumnos.insert("end", f"{sid}: {nombre} (RUT: {rut})")

    def ui_agregar_alumno(self):
        """Agrega un alumno global usando los campos del formulario"""
        nombre = self.entrada_nombre_alumno.get().strip()
        rut = self.entrada_rut_alumno.get().strip()
        if not nombre:
            messagebox.showwarning("Faltan datos", "Nombre obligatorio.")
            return
        try:
            st = self.sistema.agregar_estudiante_global(nombre, rut)
            messagebox.showinfo("Éxito", f"Alumno agregado (ID: {st.id}).")
            self.entrada_nombre_alumno.delete(0, "end")
            self.entrada_rut_alumno.delete(0, "end")
            self.refrescar_lista_alumnos()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_alumno(self):
        """Edita el alumno seleccionado con los valores actuales del formulario"""
        sel = self.listbox_alumnos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un alumno para editar.")
            return
        txt = self.listbox_alumnos.get(sel[0])
        sid = int(txt.split(":")[0])
        nuevo_nombre = self.entrada_nombre_alumno.get().strip()
        nuevo_rut = self.entrada_rut_alumno.get().strip()
        if not nuevo_nombre:
            messagebox.showwarning("Faltan datos", "Nombre obligatorio.")
            return
        try:
            self.sistema.actualizar_estudiante(sid, nuevo_nombre, nuevo_rut)
            messagebox.showinfo("Éxito", "Alumno modificado.")
            self.entrada_nombre_alumno.delete(0, "end")
            self.entrada_rut_alumno.delete(0, "end")
            self.refrescar_lista_alumnos()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_alumno(self):
        """Elimina el alumno seleccionado tras pedir confirmación"""
        sel = self.listbox_alumnos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un alumno para eliminar.")
            return
        txt = self.listbox_alumnos.get(sel[0])
        sid = int(txt.split(":")[0])
        if messagebox.askyesno("Confirmar", f"Eliminar alumno {sid}? Esto lo quita de todas las sesiones."):
            try:
                self.sistema.eliminar_estudiante(sid)
                messagebox.showinfo("Éxito", "Alumno eliminado.")
                self.refrescar_lista_alumnos()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_select(self, event=None):
        """Al seleccionar un alumno, rellenar los campos con sus datos (comodidad)"""
        sel = self.listbox_alumnos.curselection()
        if not sel:
            return
        txt = self.listbox_alumnos.get(sel[0])
        sid = int(txt.split(":")[0])
        st = self.sistema.estudiantes.get(sid)
        if not st:
            return
        try:
            self.entrada_nombre_alumno.delete(0, "end")
            self.entrada_nombre_alumno.insert(0, st.nombre)
            self.entrada_rut_alumno.delete(0, "end")
            self.entrada_rut_alumno.insert(0, st.rut)
        except Exception:
            pass

if __name__ == "__main__":
    try:
        from asistencia_app import SistemaAsistencia 
    except Exception:
        class Estudiante:
            def __init__(self, id, nombre, rut=""):
                self.id = id
                self.nombre = nombre
                self.rut = rut
            def to_dict(self): return {"id": self.id, "nombre": self.nombre, "rut": self.rut}

        class SistemaAsistencia:
            def __init__(self):
                self.estudiantes = {}
                self.siguiente_id_estudiante = 1
            def agregar_estudiante_global(self, nombre, rut=""):
                st = Estudiante(self.siguiente_id_estudiante, nombre, rut)
                self.estudiantes[st.id] = st
                self.siguiente_id_estudiante += 1
                return st
            def actualizar_estudiante(self, estudiante_id, nuevo_nombre, nuevo_rut):
                if estudiante_id not in self.estudiantes:
                    raise ValueError("Alumno no encontrado")
                st = self.estudiantes[estudiante_id]
                st.nombre = nuevo_nombre
                st.rut = nuevo_rut
                return st
            def eliminar_estudiante(self, estudiante_id):
                if estudiante_id not in self.estudiantes:
                    raise ValueError("Alumno no encontrado")
                del self.estudiantes[estudiante_id]

    class AppSimulada(ctk.CTk):
        def __init__(self, sistema):
            super().__init__()
            self.sistema = sistema
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.title("Simulación AppGUI - Alumnos")
            self.geometry("700x500")

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
    panel = AlumnosPanel(app, sistema)
    panel.frame.pack(fill="both", expand=True, padx=12, pady=12)
    app.mainloop()
