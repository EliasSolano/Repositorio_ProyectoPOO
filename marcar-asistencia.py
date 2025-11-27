import customtkinter as ctk
from tkinter import messagebox

# =========================================
# MODELO (POO)
# =========================================

class Alumno:
    def __init__(self, nombre, rut, id_alumno):
        self.nombre = nombre
        self.rut = rut
        self.id = id_alumno

    def mostrar_info(self):
        return f"ID: {self.id} | Nombre: {self.nombre} | RUT: {self.rut}"


class Curso:
    def __init__(self, nombre, horario):
        self.nombre = nombre
        self.horario = horario
        self.alumnos = []
        self.asistencia = {}  # {fecha: {id_alumno: True/False}}

    def agregar_alumno(self, alumno):
        self.alumnos.append(alumno)

    def registrar_asistencia(self, fecha, id_alumno, presente):
        if fecha not in self.asistencia:
            self.asistencia[fecha] = {}
        self.asistencia[fecha][id_alumno] = presente


class SistemaAsistencia:
    def __init__(self):
        self.cursos = []

    def crear_curso(self, nombre, horario):
        curso = Curso(nombre, horario)
        self.cursos.append(curso)
        return curso

    def buscar_curso(self, nombre):
        for c in self.cursos:
            if c.nombre == nombre:
                return c
        return None


# =========================================
# SISTEMA DE PRUEBA
# =========================================

sistema = SistemaAsistencia()

# Crear curso y alumnos de prueba
curso_demo = sistema.crear_curso("Programación", "Lunes 10:00")
curso_demo.agregar_alumno(Alumno("José Pérez", "20.456.123-4", "A01"))
curso_demo.agregar_alumno(Alumno("María Soto", "21.234.567-8", "A02"))
curso_demo.agregar_alumno(Alumno("Luis Díaz", "19.876.543-2", "A03"))

# =========================================
# GUI
# =========================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Sistema de Asistencia")
app.geometry("550x500")


# ---------------------------
# Función para registrar asistencia
# ---------------------------

def abrir_asistencia():
    ventana = ctk.CTkToplevel(app)
    ventana.title("Registrar Asistencia")
    ventana.geometry("500x500")

    # Seleccionar curso
    ctk.CTkLabel(ventana, text="Seleccionar curso:", font=("Arial", 15)).pack(pady=10)
    nombres_cursos = [c.nombre for c in sistema.cursos]
    combo_cursos = ctk.CTkComboBox(ventana, values=nombres_cursos)
    combo_cursos.pack(pady=10)

    # Fecha
    ctk.CTkLabel(ventana, text="Fecha (DD-MM-AAAA):").pack(pady=5)
    entry_fecha = ctk.CTkEntry(ventana)
    entry_fecha.pack(pady=5)

    # Frame para alumnos
    frame_alumnos = ctk.CTkScrollableFrame(ventana, width=400, height=250)
    frame_alumnos.pack(pady=15)

    checkboxes = {}

    def cargar_alumnos():
        for widget in frame_alumnos.winfo_children():
            widget.destroy()

        nombre_curso = combo_cursos.get()
        curso = sistema.buscar_curso(nombre_curso)

        if curso is None:
            return

        for alumno in curso.alumnos:
            var = ctk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(
                frame_alumnos,
                text=alumno.mostrar_info(),
                variable=var
            )
            chk.pack(anchor="w", pady=2)
            checkboxes[alumno.id] = var

    def guardar_asistencia():
        fecha = entry_fecha.get()
        nombre_curso = combo_cursos.get()
        curso = sistema.buscar_curso(nombre_curso)

        if fecha == "" or curso is None:
            messagebox.showerror("Error", "Faltan datos")
            return

        for id_alumno, variable in checkboxes.items():
            presente = variable.get()
            curso.registrar_asistencia(fecha, id_alumno, presente)

        messagebox.showinfo("Éxito", "Asistencia registrada correctamente")
        ventana.destroy()

    ctk.CTkButton(ventana, text="Cargar alumnos", command=cargar_alumnos).pack(pady=10)
    ctk.CTkButton(ventana, text="Guardar asistencia", command=guardar_asistencia).pack(pady=10)


# Botón principal
ctk.CTkButton(app, text="Registrar asistencia", width=250, height=50, command=abrir_asistencia).pack(pady=40)


app.mainloop()
