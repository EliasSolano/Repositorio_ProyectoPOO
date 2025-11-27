from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk

# -------------------------
# CLASES
# -------------------------

class Alumno:
    def __init__(self, nombre, rut, id_alumno):
        self.nombre = nombre
        self.rut = rut
        self.id_alumno = id_alumno

    def mostrar_info(self):
        return f"Nombre: {self.nombre} | RUT: {self.rut} | ID: {self.id_alumno}"


class SistemaAlumnos:
    def __init__(self):
        self.alumnos = []

    def agregar_alumno(self, alumno):
        self.alumnos.append(alumno)

    def buscar_alumno(self, id_alumno):
        for a in self.alumnos:
            if a.id_alumno == id_alumno:
                return a
        return None

    def eliminar_alumno(self, id_alumno):
        alumno = self.buscar_alumno(id_alumno)
        if alumno:
            self.alumnos.remove(alumno)
            return True
        return False

    def listar_alumnos(self):
        return [a.mostrar_info() for a in self.alumnos]


sistema = SistemaAlumnos()

# -------------------------
# FUNCIONES GUI
# -------------------------

def ventana_crear_alumno():
    def guardar():
        nombre = entry_nombre.get()
        rut = entry_rut.get()
        id_alumno = entry_id.get()

        if not nombre or not rut or not id_alumno:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return

        nuevo = Alumno(nombre, rut, id_alumno)
        sistema.agregar_alumno(nuevo)

        messagebox.showinfo("Éxito", "Alumno agregado correctamente")
        ventana.destroy()

    ventana = ctk.CTkToplevel(app)
    ventana.title("Crear Alumno")
    ventana.geometry("350x250")

    ctk.CTkLabel(ventana, text="Nombre:").pack(pady=4)
    entry_nombre = ctk.CTkEntry(ventana)
    entry_nombre.pack()

    ctk.CTkLabel(ventana, text="RUT:").pack(pady=4)
    entry_rut = ctk.CTkEntry(ventana)
    entry_rut.pack()

    ctk.CTkLabel(ventana, text="ID:").pack(pady=4)
    entry_id = ctk.CTkEntry(ventana)
    entry_id.pack()

    ctk.CTkButton(ventana, text="Guardar", command=guardar).pack(pady=10)


def ventana_modificar_alumno():
    def cargar():
        alumno = sistema.buscar_alumno(entry_buscar.get())
        if alumno:
            entry_nombre.delete(0, "end")
            entry_rut.delete(0, "end")

            entry_nombre.insert(0, alumno.nombre)
            entry_rut.insert(0, alumno.rut)

        else:
            messagebox.showerror("Error", "Alumno no encontrado")

    def guardar_cambios():
        alumno = sistema.buscar_alumno(entry_buscar.get())
        if alumno:
            alumno.nombre = entry_nombre.get()
            alumno.rut = entry_rut.get()
            messagebox.showinfo("Éxito", "Alumno modificado")
            ventana.destroy()
        else:
            messagebox.showerror("Error", "Alumno no encontrado")

    ventana = ctk.CTkToplevel(app)
    ventana.title("Modificar Alumno")
    ventana.geometry("350x300")

    ctk.CTkLabel(ventana, text="ID del alumno a modificar:").pack()
    entry_buscar = ctk.CTkEntry(ventana)
    entry_buscar.pack(pady=5)

    ctk.CTkButton(ventana, text="Cargar alumno", command=cargar).pack(pady=5)

    ctk.CTkLabel(ventana, text="Nombre nuevo:").pack()
    entry_nombre = ctk.CTkEntry(ventana)
    entry_nombre.pack(pady=5)

    ctk.CTkLabel(ventana, text="RUT nuevo:").pack()
    entry_rut = ctk.CTkEntry(ventana)
    entry_rut.pack(pady=5)

    ctk.CTkButton(ventana, text="Guardar cambios", command=guardar_cambios).pack(pady=10)


def ventana_eliminar_alumno():
    def eliminar():
        if sistema.eliminar_alumno(entry_id.get()):
            messagebox.showinfo("Éxito", "Alumno eliminado")
            ventana.destroy()
        else:
            messagebox.showerror("Error", "Alumno no encontrado")

    ventana = ctk.CTkToplevel(app)
    ventana.title("Eliminar Alumno")
    ventana.geometry("300x160")

    ctk.CTkLabel(ventana, text="ID del alumno:").pack(pady=5)
    entry_id = ctk.CTkEntry(ventana)
    entry_id.pack()

    ctk.CTkButton(ventana, text="Eliminar", command=eliminar).pack(pady=10)


def ventana_mostrar_alumnos():
    ventana = ctk.CTkToplevel(app)
    ventana.title("Lista de Alumnos")
    ventana.geometry("400x400")

    lista = sistema.listar_alumnos()

    if not lista:
        ctk.CTkLabel(ventana, text="No hay alumnos registrados").pack(pady=10)
        return

    for alumno in lista:
        ctk.CTkLabel(ventana, text=alumno).pack(pady=3)


# -------------------------
# VENTANA PRINCIPAL
# -------------------------

app = ctk.CTk()
app.title("Administración de Alumnos")
app.geometry("400x350")

ctk.CTkLabel(app, text="Administración de Alumnos", font=("Arial", 20)).pack(pady=15)

ctk.CTkButton(app, text="Crear alumno", width=200, command=ventana_crear_alumno).pack(pady=10)
ctk.CTkButton(app, text="Modificar alumno", width=200, command=ventana_modificar_alumno).pack(pady=10)
ctk.CTkButton(app, text="Eliminar alumno", width=200, command=ventana_eliminar_alumno).pack(pady=10)
ctk.CTkButton(app, text="Mostrar alumnos", width=200, command=ventana_mostrar_alumnos).pack(pady=10)

app.mainloop()
