import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Lista temporal de cursos (después se conecta con JSON)
cursos = []

# ---------------------------
# FUNCIONES BÁSICAS
# ---------------------------

def crear_curso():
    def guardar():
        nombre = entry_nombre.get()
        horario = entry_horario.get()

        if nombre == "" or horario == "":
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return

        cursos.append({"nombre": nombre, "horario": horario})
        messagebox.showinfo("Éxito", f"Curso '{nombre}' creado")
        ventana.destroy()

    ventana = ctk.CTkToplevel(app)
    ventana.title("Crear Curso")
    ventana.geometry("350x200")

    ctk.CTkLabel(ventana, text="Nombre del curso:").pack(pady=5)
    entry_nombre = ctk.CTkEntry(ventana)
    entry_nombre.pack()

    ctk.CTkLabel(ventana, text="Horario:").pack(pady=5)
    entry_horario = ctk.CTkEntry(ventana)
    entry_horario.pack()

    ctk.CTkButton(ventana, text="Guardar", command=guardar).pack(pady=10)


def modificar_curso():
    def cargar_curso():
        nombre_buscar = entry_buscar.get()
        for curso in cursos:
            if curso["nombre"] == nombre_buscar:
                entry_nombre.delete(0, "end")
                entry_horario.delete(0, "end")
                entry_nombre.insert(0, curso["nombre"])
                entry_horario.insert(0, curso["horario"])
                return
        messagebox.showerror("Error", "Curso no encontrado")

    def guardar_cambios():
        original = entry_buscar.get()
        nuevo_nombre = entry_nombre.get()
        nuevo_horario = entry_horario.get()

        for curso in cursos:
            if curso["nombre"] == original:
                curso["nombre"] = nuevo_nombre
                curso["horario"] = nuevo_horario
                messagebox.showinfo("Éxito", "Curso modificado")
                ventana.destroy()
                return

        messagebox.showerror("Error", "Curso no encontrado")

    ventana = ctk.CTkToplevel(app)
    ventana.title("Modificar Curso")
    ventana.geometry("350x250")

    ctk.CTkLabel(ventana, text="Nombre del curso a modificar:").pack()
    entry_buscar = ctk.CTkEntry(ventana)
    entry_buscar.pack(pady=5)

    ctk.CTkButton(ventana, text="Cargar", command=cargar_curso).pack(pady=5)

    ctk.CTkLabel(ventana, text="Nuevo nombre:").pack()
    entry_nombre = ctk.CTkEntry(ventana)
    entry_nombre.pack(pady=5)

    ctk.CTkLabel(ventana, text="Nuevo horario:").pack()
    entry_horario = ctk.CTkEntry(ventana)
    entry_horario.pack(pady=5)

    ctk.CTkButton(ventana, text="Guardar cambios", command=guardar_cambios).pack(pady=10)


def eliminar_curso():
    def eliminar():
        nombre = entry_nombre.get()
        global cursos
        for curso in cursos:
            if curso["nombre"] == nombre:
                cursos.remove(curso)
                messagebox.showinfo("Éxito", f"Curso '{nombre}' eliminado")
                ventana.destroy()
                return
        messagebox.showerror("Error", "Curso no encontrado")

    ventana = ctk.CTkToplevel(app)
    ventana.title("Eliminar Curso")
    ventana.geometry("300x150")

    ctk.CTkLabel(ventana, text="Nombre del curso:").pack(pady=5)
    entry_nombre = ctk.CTkEntry(ventana)
    entry_nombre.pack()

    ctk.CTkButton(ventana, text="Eliminar", command=eliminar).pack(pady=10)


# ---------------------------
# VENTANA PRINCIPAL
# ---------------------------

app = ctk.CTk()
app.title("Sistema de Asistencia - Cursos")
app.geometry("400x300")

ctk.CTkLabel(app, text="Administración de Cursos", font=("Arial", 20)).pack(pady=15)

ctk.CTkButton(app, text="Crear curso", width=200, command=crear_curso).pack(pady=10)
ctk.CTkButton(app, text="Modificar curso", width=200, command=modificar_curso).pack(pady=10)
ctk.CTkButton(app, text="Eliminar curso", width=200, command=eliminar_curso).pack(pady=10)

app.mainloop()
