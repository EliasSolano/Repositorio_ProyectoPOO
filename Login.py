import tkinter
import customtkinter as ctk
import json
import re
import os

Usuarios = "usuarios.json"  # Json para guardar usuarios

def cargar_usuarios():  # Función para cargar usuarios desde el Json
    if not os.path.exists(Usuarios):
        return {}
    with open(Usuarios, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(usuarios):  # Función para guardar usuarios en el JSON
    with open(Usuarios, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

def es_valido(texto):  # Función para validar que solo sean letras y números
    return bool(re.match("^[A-Za-z0-9]+$", texto))

def generar_id(usuarios): # Función para generar ID único
    """Genera un ID incremental basado en los existentes"""
    if not usuarios:
        return 1
    ids = [datos["id"] for datos in usuarios.values()]
    return max(ids) + 1

def registrar():  # Función para registrar usuario
    usuario = entry_usuario.get()
    contrasena = entry_contrasena.get()
    usuarios = cargar_usuarios()

    if not usuario or not contrasena:  # Error cuando falta usuario o contraseña
        label_mensaje.configure(text="Error: El Usuario y contraseña no pueden estar vacíos", text_color="red")
        return

    if not es_valido(usuario) or not es_valido(contrasena):  # Error cuando hay otros caracteres
        label_mensaje.configure(text="Error: Solo se puede rellenar con letras y números", text_color="red")
        return

    if usuario in usuarios:  # Error cuando se crea un usuario que ya existe
        label_mensaje.configure(text="Error: El usuario ya existe", text_color="red")
        return

    # Generar ID único
    nuevo_id = generar_id(usuarios)

    # Guardar usuario con contraseña e ID
    usuarios[usuario] = {"contrasena": contrasena, "id": nuevo_id}
    guardar_usuarios(usuarios)
    label_mensaje.configure(text=f"Usuario registrado con éxito", text_color="green")

def iniciar_sesion():  # Función para iniciar sesión
    usuario = entry_usuario.get()
    contrasena = entry_contrasena.get()
    usuarios = cargar_usuarios()

    if usuario in usuarios and usuarios[usuario]["contrasena"] == contrasena:
        user_id = usuarios[usuario]["id"]
        label_mensaje.configure(text=f"Inicio de sesión exitoso", text_color="green")
        # Luego de aquí se abrirá el programa de asistencia
    else:
        label_mensaje.configure(text="Usuario o contraseña incorrecto", text_color="red")


ventana = ctk.CTk()
ventana.title("Login: Sistema de asistencia") #Nombre de ventana
ventana.geometry("400x300") # Tamaño de ventana

ctk.set_appearance_mode("system") # Agarra el color del sistema
ctk.set_default_color_theme("green") # Color verde para widgets

label_titulo = ctk.CTkLabel(ventana, text="Sistema de asistencia", font=("Arial", 20))
label_titulo.pack(pady=10)

entry_usuario = ctk.CTkEntry(ventana, placeholder_text="Usuario")
entry_usuario.pack(pady=5)

entry_contrasena = ctk.CTkEntry(ventana, placeholder_text="Contraseña", show="*")
entry_contrasena.pack(pady=5)

btn_login = ctk.CTkButton(ventana, text="Iniciar Sesión", command=iniciar_sesion)
btn_login.pack(pady=5)

btn_registro = ctk.CTkButton(ventana, text="Registrarse", command=registrar)
btn_registro.pack(pady=5)

label_mensaje = ctk.CTkLabel(ventana, text="")
label_mensaje.pack(pady=10)

ventana.mainloop()

#Puto el que lo lea
#En especial benja