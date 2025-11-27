from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

class SesionesPanel:

    def __init__(self, app_gui, sistema):
        self.app = app_gui
        self.sistema = sistema

        parent = getattr(self.app, "contenido", self.app)
        self.frame = ctk.CTkFrame(parent)

        top = ctk.CTkFrame(self.frame)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Sesiones por curso", font=("Arial", 14)).pack(side="left", padx=6)

        acciones = ctk.CTkFrame(top)
        acciones.pack(side="right", padx=6)
        ctk.CTkButton(acciones, text="Crear sesión (curso seleccionado)", command=self.ui_iniciar_sesion).pack(side="left", padx=6)
        ctk.CTkButton(acciones, text="Editar presentes (sesión seleccionada)", command=self.ui_editar_presentes_sesion).pack(side="left", padx=6)
        ctk.CTkButton(acciones, text="Eliminar sesión", command=self.ui_eliminar_sesion).pack(side="left", padx=6)

        mid = ctk.CTkFrame(self.frame)
        mid.pack(fill="x", padx=6, pady=6)

        # Combo de cursos
        self.combo_curso_sesiones = ctk.CTkComboBox(mid, values=list(self.sistema.cursos.keys()))
        self.combo_curso_sesiones.pack(side="left", padx=6)
        self.combo_curso_sesiones.configure(command=self.on_cambio_curso_sesiones)

        # lista de alumnos
        leftf = ctk.CTkFrame(self.frame)
        leftf.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(leftf, text="Alumnos (seleccione múltiples con Ctrl/Shift)").pack(anchor="w", padx=4)
        self.listbox_alumnos_sesiones = tk.Listbox(leftf, selectmode="extended")
        self.listbox_alumnos_sesiones.pack(fill="both", expand=True, padx=4, pady=4)

        #Botón para marcar seleccionados como presentes
        btns_left = ctk.CTkFrame(leftf)
        btns_left.pack(pady=6)
        ctk.CTkButton(btns_left, text="Marcar seleccionados como presentes", command=self.ui_marcar_presentes_seleccionados).pack()

        #lista de sesiones
        rightf = ctk.CTkFrame(self.frame)
        rightf.pack(side="right", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(rightf, text="Sesiones (seleccione una)").pack(anchor="w", padx=4)
        self.listbox_sesiones = tk.Listbox(rightf, height=16)
        self.listbox_sesiones.pack(fill="both", expand=True, padx=4, pady=4)
        self.listbox_sesiones.bind("<<ListboxSelect>>", lambda e: None)

        # Inicializar listas
        self.refrescar_combo_cursos()
        self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get() if self.combo_curso_sesiones.get() else None)

    def refrescar_combo_cursos(self):
        """Actualiza las opciones del combo con los códigos de curso actuales."""
        try:
            valores = list(self.sistema.cursos.keys())
        except Exception:
            valores = []
        self.combo_curso_sesiones.configure(values=valores)

    def on_cambio_curso_sesiones(self, val):
        """
        Cuando cambia el curso seleccionado:
        - pobla la lista de alumnos (globales)
        - pobla la lista de sesiones del curso
        """
        self.listbox_alumnos_sesiones.delete(0, "end")
        self.listbox_sesiones.delete(0, "end")
        if not val:
            return
        try:
            for sid, st in sorted(self.sistema.estudiantes.items()):
                nombre = getattr(st, "nombre", str(st))
                rut = getattr(st, "rut", "")
                self.listbox_alumnos_sesiones.insert("end", f"{sid}: {nombre} (RUT: {rut})")
        except Exception:
            pass
        try:
            sesiones = self.sistema.obtener_sesiones_por_curso(val)
            for s in sorted(sesiones, key=lambda x: x.fecha, reverse=True):
                self.listbox_sesiones.insert("end", f"{s.id} - {s.fecha.strftime('%Y-%m-%d %H:%M')} | Presentes: {len(s.ids_presentes)}")
        except Exception:
            pass

    def ui_iniciar_sesion(self):
        """Crea una nueva sesión para el curso seleccionado."""
        codigo_curso = self.combo_curso_sesiones.get()
        if not codigo_curso:
            messagebox.showwarning("Seleccione curso", "Seleccione un curso primero.")
            return
        try:
            s = self.sistema.iniciar_sesion(codigo_curso)
            messagebox.showinfo("Éxito", f"Sesión {s.id} creada.")
            self.on_cambio_curso_sesiones(codigo_curso)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_marcar_presentes_seleccionados(self):
        """Marca como presentes los alumnos seleccionados en la sesión seleccionada."""
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        sels = self.listbox_alumnos_sesiones.curselection()
        if not sels:
            messagebox.showwarning("Seleccione alumnos", "Seleccione uno o más alumnos.")
            return
        sids = [int(self.listbox_alumnos_sesiones.get(i).split(":")[0]) for i in sels]
        try:
            self.sistema.marcar_presentes_multiple(sess_id, sids)
            messagebox.showinfo("Éxito", f"Marcados {len(sids)} presentes en sesión {sess_id}.")
            self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_presentes_sesion(self):
        """Abre un diálogo con checkboxes para editar la lista de presentes de una sesión."""
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión para editar.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        sess = self.sistema.sesiones.get(sess_id) if hasattr(self.sistema, "sesiones") else None
        if not sess:
            messagebox.showerror("Error", "Sesión no encontrada")
            return

        top = tk.Toplevel(self.app)
        top.title(f"Editar asistentes - Sesión {sess_id}")
        top.geometry("420x520")
        tk.Label(top, text=f"Sesión {sess.id} - {sess.fecha.strftime('%Y-%m-%d %H:%M')} (Curso: {sess.codigo_curso})").pack(pady=6)
        frame = tk.Frame(top)
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        var_map = {}
        try:
            for sid, st in sorted(self.sistema.estudiantes.items()):
                var = tk.IntVar(value=1 if sid in sess.ids_presentes else 0)
                cb = tk.Checkbutton(frame, text=f"{sid}: {st.nombre}", variable=var)
                cb.pack(anchor="w")
                var_map[sid] = var
        except Exception:
            pass

        def aplicar_cambios():
            nuevos_presentes = [sid for sid, var in var_map.items() if var.get() == 1]
            try:
                self.sistema.editar_sesion(sess_id, nuevos_ids_presentes=nuevos_presentes)
                messagebox.showinfo("Éxito", "Presentes actualizados.")
                top.destroy()
                self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(top, text="Guardar cambios", command=aplicar_cambios).pack(pady=8)
        tk.Button(top, text="Cancelar", command=top.destroy).pack(pady=4)

    def ui_eliminar_sesion(self):
        """Elimina la sesión seleccionada tras pedir confirmación."""
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión para eliminar.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        if messagebox.askyesno("Confirmar", f"Eliminar sesión {sess_id}?"):
            try:
                self.sistema.eliminar_sesion(sess_id)
                messagebox.showinfo("Éxito", "Sesión eliminada.")
                self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
            except Exception as e:
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    try:
        from asistencia_app import SistemaAsistencia 
    except Exception:

        from datetime import datetime

        class SesionMin:
            def __init__(self, id, codigo_curso, fecha, ids_presentes=None):
                self.id = id
                self.codigo_curso = codigo_curso
                self.fecha = fecha
                self.ids_presentes = ids_presentes or []

        class EstudianteMin:
            def __init__(self, id, nombre, rut=""):
                self.id = id
                self.nombre = nombre
                self.rut = rut

        class CursoMin:
            def __init__(self, codigo, nombre, horario=""):
                self.codigo = codigo
                self.nombre = nombre
                self.horario = horario

        class SistemaAsistencia:
            def __init__(self):
                self.cursos = {"CS101": CursoMin("CS101", "Intro CS"), "MATH1": CursoMin("MATH1", "Matemáticas")}
                self.estudiantes = {1: EstudianteMin(1, "Ana"), 2: EstudianteMin(2, "Luis"), 3: EstudianteMin(3, "María")}
                self.sesiones = {}
                self.siguiente_id_sesion = 1

            def iniciar_sesion(self, codigo_curso):
                if codigo_curso not in self.cursos:
                    raise ValueError("Curso no encontrado")
                s = SesionMin(self.siguiente_id_sesion, codigo_curso, datetime.now(), [])
                self.sesiones[s.id] = s
                self.siguiente_id_sesion += 1
                return s

            def obtener_sesiones_por_curso(self, codigo_curso):
                return [s for s in self.sesiones.values() if s.codigo_curso == codigo_curso]

            def marcar_presentes_multiple(self, sesion_id, ids_estudiantes):
                sess = self.sesiones.get(sesion_id)
                if not sess:
                    raise ValueError("Sesión no encontrada")
                for sid in ids_estudiantes:
                    if sid not in sess.ids_presentes and sid in self.estudiantes:
                        sess.ids_presentes.append(sid)

            def editar_sesion(self, sesion_id, nueva_fecha=None, nuevos_ids_presentes=None):
                sess = self.sesiones.get(sesion_id)
                if not sess:
                    raise ValueError("Sesión no encontrada")
                if nueva_fecha:
                    sess.fecha = nueva_fecha
                if nuevos_ids_presentes is not None:
                    sess.ids_presentes = [sid for sid in nuevos_ids_presentes if sid in self.estudiantes]

            def eliminar_sesion(self, sesion_id):
                if sesion_id not in self.sesiones:
                    raise ValueError("Sesión no encontrada")
                del self.sesiones[sesion_id]

    class AppSimulada(ctk.CTk):
        def __init__(self, sistema):
            super().__init__()
            self.sistema = sistema
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.title("Simulación AppGUI - Sesiones")
            self.geometry("900x600")

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
    panel = SesionesPanel(app, sistema)
    panel.frame.pack(fill="both", expand=True, padx=12, pady=12)
    app.mainloop()
