from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk

# ----------------------
# Archivos de persistencia
# ----------------------
ARCHIVO_DATOS = "datos.json"
ARCHIVO_USUARIOS = "usuarios.json"

# ----------------------
# Modelos (clases simples)
# ----------------------
class Estudiante:
    def __init__(self, id: int, nombre: str, rut: Optional[str] = ""):
        self.id = id
        self.nombre = nombre
        self.rut = rut

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "nombre": self.nombre, "rut": self.rut}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Estudiante":
        return Estudiante(d["id"], d["nombre"], d.get("rut", ""))


class Curso:
    def __init__(self, codigo: str, nombre: str, horario: Optional[str] = ""):
        self.codigo = codigo
        self.nombre = nombre
        self.horario = horario

    def to_dict(self) -> Dict[str, Any]:
        return {"codigo": self.codigo, "nombre": self.nombre, "horario": self.horario}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Curso":
        return Curso(d["codigo"], d["nombre"], d.get("horario", ""))


class Sesion:
    def __init__(self, id: int, codigo_curso: str, fecha: datetime, ids_presentes: List[int]):
        self.id = id
        self.codigo_curso = codigo_curso
        self.fecha = fecha
        self.ids_presentes = ids_presentes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "codigo_curso": self.codigo_curso,
            "fecha": self.fecha.isoformat(),
            "ids_presentes": self.ids_presentes
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Sesion":
        return Sesion(d["id"], d["codigo_curso"], datetime.fromisoformat(d["fecha"]),
                      d.get("ids_presentes", []))


# ----------------------
# Sistema (lógica + persistencia)
# ----------------------
class SistemaAsistencia:
    def __init__(self, archivo_datos: str = ARCHIVO_DATOS, archivo_usuarios: str = ARCHIVO_USUARIOS):
        self.archivo_datos = archivo_datos
        self.archivo_usuarios = archivo_usuarios

        # diccionario global de estudiantes: id -> Estudiante
        self.estudiantes: Dict[int, Estudiante] = {}
        # diccionario de cursos: codigo -> Curso
        self.cursos: Dict[str, Curso] = {}
        # diccionario de sesiones: id -> Sesion
        self.sesiones: Dict[int, Sesion] = {}

        self.siguiente_id_estudiante = 1
        self.siguiente_id_sesion = 1

        # usuarios: nombre_usuario -> {id, contaseña}
        self.usuarios: Dict[str, Dict[str, Any]] = {}

        self.cargar_todo()

    # --- persistencia ---
    def cargar_todo(self):
        # datos: estudiantes, cursos, sesiones, siguientes ids
        if not os.path.exists(self.archivo_datos):
            self._guardar_datos()
        with open(self.archivo_datos, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
            except json.JSONDecodeError:
                datos = {}

        self.estudiantes = {}
        for s in datos.get("estudiantes", []):
            st = Estudiante.from_dict(s)
            self.estudiantes[st.id] = st

        self.cursos = {}
        for c in datos.get("cursos", []):
            co = Curso.from_dict(c)
            self.cursos[co.codigo] = co

        self.sesiones = {}
        for se in datos.get("sesiones", []):
            sess = Sesion.from_dict(se)
            self.sesiones[sess.id] = sess

        self.siguiente_id_estudiante = datos.get("siguiente_id_estudiante", self.siguiente_id_estudiante)
        self.siguiente_id_sesion = datos.get("siguiente_id_sesion", self.siguiente_id_sesion)

        # usuarios
        if not os.path.exists(self.archivo_usuarios):
            self._guardar_usuarios()
        with open(self.archivo_usuarios, "r", encoding="utf-8") as f:
            try:
                self.usuarios = json.load(f)
            except json.JSONDecodeError:
                self.usuarios = {}

    def _guardar_datos(self):
        datos = {
            "estudiantes": [s.to_dict() for s in self.estudiantes.values()],
            "cursos": [c.to_dict() for c in self.cursos.values()],
            "sesiones": [s.to_dict() for s in self.sesiones.values()],
            "siguiente_id_estudiante": self.siguiente_id_estudiante,
            "siguiente_id_sesion": self.siguiente_id_sesion
        }
        with open(self.archivo_datos, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def _guardar_usuarios(self):
        with open(self.archivo_usuarios, "w", encoding="utf-8") as f:
            json.dump(self.usuarios, f, ensure_ascii=False, indent=2)

    def guardar_todo(self):
        self._guardar_datos()
        self._guardar_usuarios()

    # --- estudiantes (globales) ---
    def agregar_estudiante_global(self, nombre: str, rut: str = "") -> Estudiante:
        st = Estudiante(self.siguiente_id_estudiante, nombre, rut)
        self.estudiantes[st.id] = st
        self.siguiente_id_estudiante += 1
        self._guardar_datos()
        return st

    def actualizar_estudiante(self, estudiante_id: int, nuevo_nombre: str, nuevo_rut: str) -> Estudiante:
        st = self.estudiantes.get(estudiante_id)
        if not st:
            raise ValueError("Alumno no encontrado")
        st.nombre = nuevo_nombre
        st.rut = nuevo_rut
        self._guardar_datos()
        return st

    def eliminar_estudiante(self, estudiante_id: int):
        if estudiante_id not in self.estudiantes:
            raise ValueError("Alumno no encontrado")
        # eliminar del sistema (y de todas las listas de presentes de las sesiones)
        del self.estudiantes[estudiante_id]
        for sess in self.sesiones.values():
            if estudiante_id in sess.ids_presentes:
                sess.ids_presentes.remove(estudiante_id)
        self._guardar_datos()

    # --- cursos ---
    def crear_curso(self, codigo: str, nombre: str, horario: str = "") -> Curso:
        if codigo in self.cursos:
            raise ValueError("Código de curso ya existe")
        co = Curso(codigo, nombre, horario)
        self.cursos[codigo] = co
        self._guardar_datos()
        return co

    def actualizar_curso(self, codigo_antiguo: str, codigo_nuevo: str, nombre: str, horario: str) -> Curso:
        if codigo_antiguo not in self.cursos:
            raise ValueError("Curso no encontrado")
        if codigo_nuevo != codigo_antiguo and codigo_nuevo in self.cursos:
            raise ValueError("Nuevo código ya existe")
        co = self.cursos.pop(codigo_antiguo)
        co.codigo = codigo_nuevo
        co.nombre = nombre
        co.horario = horario
        self.cursos[codigo_nuevo] = co
        # actualizar sesiones que referencian el curso
        for s in self.sesiones.values():
            if s.codigo_curso == codigo_antiguo:
                s.codigo_curso = codigo_nuevo
        self._guardar_datos()
        return co

    def eliminar_curso(self, codigo: str):
        if codigo not in self.cursos:
            raise ValueError("Curso no encontrado")
        del self.cursos[codigo]
        # eliminar sesiones asociadas
        self.sesiones = {sid: s for sid, s in self.sesiones.items() if s.codigo_curso != codigo}
        self._guardar_datos()

    # --- sesiones ---
    def iniciar_sesion(self, codigo_curso: str) -> Sesion:
        if codigo_curso not in self.cursos:
            raise ValueError("Curso no encontrado")
        sess = Sesion(self.siguiente_id_sesion, codigo_curso, datetime.now(), [])
        self.sesiones[sess.id] = sess
        self.siguiente_id_sesion += 1
        self._guardar_datos()
        return sess

    def editar_sesion(self, sesion_id: int, nueva_fecha: Optional[datetime] = None, nuevos_ids_presentes: Optional[List[int]] = None):
        sess = self.sesiones.get(sesion_id)
        if not sess:
            raise ValueError("Sesión no encontrada")
        if nueva_fecha:
            sess.fecha = nueva_fecha
        if nuevos_ids_presentes is not None:
            # validar ids existentes
            ids_validos = set(self.estudiantes.keys())
            sess.ids_presentes = [sid for sid in nuevos_ids_presentes if sid in ids_validos]
        self._guardar_datos()

    def eliminar_sesion(self, sesion_id: int):
        if sesion_id not in self.sesiones:
            raise ValueError("Sesión no encontrada")
        del self.sesiones[sesion_id]
        self._guardar_datos()

    def marcar_presentes_multiple(self, sesion_id: int, ids_estudiantes: List[int]):
        sess = self.sesiones.get(sesion_id)
        if not sess:
            raise ValueError("Sesión no encontrada")
        ids_validos = set(self.estudiantes.keys())
        for sid in ids_estudiantes:
            if sid in ids_validos and sid not in sess.ids_presentes:
                sess.ids_presentes.append(sid)
        self._guardar_datos()

    # --- estadísticas ---
    def porcentaje_asistencia_por_estudiante(self, codigo_curso: str, estudiante_id: int) -> float:
        sesiones = [s for s in self.sesiones.values() if s.codigo_curso == codigo_curso]
        if not sesiones:
            return 0.0
        asistido = sum(1 for s in sesiones if estudiante_id in s.ids_presentes)
        return (asistido / len(sesiones)) * 100.0

    def obtener_sesiones_por_curso(self, codigo_curso: str) -> List[Sesion]:
        return [s for s in self.sesiones.values() if s.codigo_curso == codigo_curso]

    # --- usuarios (login simple) ---
    def registrar_usuario(self, nombre_usuario: str, password: str) -> bool:
        if nombre_usuario in self.usuarios:
            return False
        uid = max([u["id"] for u in self.usuarios.values()], default=0) + 1
        self.usuarios[nombre_usuario] = {"id": uid, "password": password}
        self._guardar_usuarios()
        return True

    def verificar_usuario(self, nombre_usuario: str, password: str) -> bool:
        u = self.usuarios.get(nombre_usuario)
        return bool(u and u.get("password") == password)


# ----------------------
# GUI único (con pestañas vistas)
# ----------------------
class AppGUI(ctk.CTk):
    def __init__(self, sistema: SistemaAsistencia):
        super().__init__()
        self.sistema = sistema
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.title("Sistema de Asistencia (simple)")
        self.geometry("1000x650")

        self.usuario_logueado: Optional[str] = None

        # Header
        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=8, pady=6)
        self.etiqueta_titulo = ctk.CTkLabel(header, text="Sistema de Asistencia", font=("Arial", 20))
        self.etiqueta_titulo.pack(side="left", padx=8)
        self.etiqueta_usuario = ctk.CTkLabel(header, text="Sin sesión")
        self.etiqueta_usuario.pack(side="right", padx=8)
        self.boton_logout = ctk.CTkButton(header, text="Logout", command=self.logout, state="disabled")
        self.boton_logout.pack(side="right", padx=8)

        # Navigation buttons
        nav = ctk.CTkFrame(self)
        nav.pack(side="top", fill="x", padx=8, pady=6)
        self.btn_vista_login = ctk.CTkButton(nav, text="Login", command=self.mostrar_login)
        self.btn_vista_cursos = ctk.CTkButton(nav, text="Cursos", command=self.mostrar_cursos)
        self.btn_vista_alumnos = ctk.CTkButton(nav, text="Alumnos", command=self.mostrar_alumnos)
        self.btn_vista_sesiones = ctk.CTkButton(nav, text="Sesiones", command=self.mostrar_sesiones)
        self.btn_vista_porcentajes = ctk.CTkButton(nav, text="Porcentajes", command=self.mostrar_porcentajes)
        for b in (self.btn_vista_login, self.btn_vista_cursos, self.btn_vista_alumnos, self.btn_vista_sesiones, self.btn_vista_porcentajes):
            b.pack(side="left", padx=6)

        # Content container
        self.contenido = ctk.CTkFrame(self)
        self.contenido.pack(side="top", fill="both", expand=True, padx=8, pady=6)

        # Build frames but don't pack yet
        self.frame_login = self.construir_frame_login()
        self.frame_cursos = None
        self.frame_alumnos = None
        self.frame_sesiones = None
        self.frame_porcentajes = None

        self.mostrar_login()

    # ----------------------
    # Construcción de frames
    # ----------------------
    def construir_frame_login(self):
        frm = ctk.CTkFrame(self.contenido)

        lbl = ctk.CTkLabel(frm, text="Iniciar sesión o registrarse", font=("Arial", 16))
        lbl.pack(pady=10)

        self.entrada_usuario_login = ctk.CTkEntry(frm, placeholder_text="Usuario")
        self.entrada_usuario_login.pack(pady=6)
        self.entrada_pass_login = ctk.CTkEntry(frm, placeholder_text="Contraseña", show="*")
        self.entrada_pass_login.pack(pady=6)

        btn_login = ctk.CTkButton(frm, text="Iniciar sesión", command=self.accion_login)
        btn_register = ctk.CTkButton(frm, text="Registrarse", command=self.accion_registrar)
        btn_login.pack(pady=6)
        btn_register.pack(pady=6)

        self.mensaje_login = ctk.CTkLabel(frm, text="")
        self.mensaje_login.pack(pady=6)

        return frm

    def construir_frame_cursos(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Crear / Modificar Cursos", font=("Arial", 14)).pack(side="left", padx=6)

        # campos
        campos = ctk.CTkFrame(frm)
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

        # listbox cursos
        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox_cursos = tk.Listbox(listf, height=14)
        self.listbox_cursos.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(listf, command=self.listbox_cursos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_cursos.config(yscrollcommand=sb.set)
        self.listbox_cursos.bind("<<ListboxSelect>>", self.llenar_formulario_curso)

        return frm

    def construir_frame_alumnos(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Alumnos (globales, estarán en todas las clases)", font=("Arial", 14)).pack(side="left", padx=6)

        campos = ctk.CTkFrame(frm)
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

        # listbox alumnos
        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox_alumnos = tk.Listbox(listf, height=16)
        self.listbox_alumnos.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(listf, command=self.listbox_alumnos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_alumnos.config(yscrollcommand=sb.set)
        self.listbox_alumnos.bind("<<ListboxSelect>>", lambda e: None)

        return frm

    def construir_frame_sesiones(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Sesiones por curso", font=("Arial", 14)).pack(side="left", padx=6)
        acciones = ctk.CTkFrame(top)
        acciones.pack(side="right", padx=6)
        ctk.CTkButton(acciones, text="Crear sesión (curso seleccionado)", command=self.ui_iniciar_sesion).pack(side="left", padx=6)
        ctk.CTkButton(acciones, text="Editar presentes (sesión seleccionada)", command=self.ui_editar_presentes_sesion).pack(side="left", padx=6)
        ctk.CTkButton(acciones, text="Eliminar sesión", command=self.ui_eliminar_sesion).pack(side="left", padx=6)

        mid = ctk.CTkFrame(frm)
        mid.pack(fill="x", padx=6, pady=6)
        # elección de curso
        self.combo_curso_sesiones = ctk.CTkComboBox(mid, values=list(self.sistema.cursos.keys()))
        self.combo_curso_sesiones.pack(side="left", padx=6)
        self.combo_curso_sesiones.configure(command=self.on_cambio_curso_sesiones)

        # lista de alumnos (multi-select)
        leftf = ctk.CTkFrame(frm)
        leftf.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(leftf, text="Alumnos (seleccione múltiples con Ctrl/Shift)").pack(anchor="w", padx=4)
        self.listbox_alumnos_sesiones = tk.Listbox(leftf, selectmode="extended")
        self.listbox_alumnos_sesiones.pack(fill="both", expand=True, padx=4, pady=4)

        # lista de sesiones
        rightf = ctk.CTkFrame(frm)
        rightf.pack(side="right", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(rightf, text="Sesiones (seleccione una)").pack(anchor="w", padx=4)
        self.listbox_sesiones = tk.Listbox(rightf, height=16)
        self.listbox_sesiones.pack(fill="both", expand=True, padx=4, pady=4)
        self.listbox_sesiones.bind("<<ListboxSelect>>", lambda e: None)

        return frm

    def construir_frame_porcentajes(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=6, pady=6)
        ctk.CTkLabel(top, text="Porcentajes por curso", font=("Arial", 14)).pack(side="left", padx=6)

        self.combo_curso_porcentajes = ctk.CTkComboBox(frm, values=list(self.sistema.cursos.keys()))
        self.combo_curso_porcentajes.pack(padx=6, pady=6)
        self.combo_curso_porcentajes.configure(command=self.refrescar_lista_porcentajes)

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox_porcentajes = tk.Listbox(listf)
        self.listbox_porcentajes.pack(fill="both", expand=True, padx=4, pady=4)

        return frm

    # ----------------------
    # Mostrar frames
    # ----------------------
    def limpiar_contenido(self):
        for w in self.contenido.winfo_children():
            w.pack_forget()

    def mostrar_login(self):
        self.limpiar_contenido()
        self.etiqueta_usuario.configure(text="Sin sesión")
        self.boton_logout.configure(state="disabled")
        self.frame_login.pack(fill="both", expand=True)

    def mostrar_cursos(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_cursos:
            self.frame_cursos = self.construir_frame_cursos()
        self.frame_cursos.pack(fill="both", expand=True)
        self.refrescar_lista_cursos()

    def mostrar_alumnos(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_alumnos:
            self.frame_alumnos = self.construir_frame_alumnos()
        self.frame_alumnos.pack(fill="both", expand=True)
        self.refrescar_lista_alumnos()

    def mostrar_sesiones(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_sesiones:
            self.frame_sesiones = self.construir_frame_sesiones()
        # refrescar opciones de cursos y listas
        self.combo_curso_sesiones.configure(values=list(self.sistema.cursos.keys()))
        self.frame_sesiones.pack(fill="both", expand=True)

    def mostrar_porcentajes(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_porcentajes:
            self.frame_porcentajes = self.construir_frame_porcentajes()
        self.frame_porcentajes.pack(fill="both", expand=True)
        self.combo_curso_porcentajes.configure(values=list(self.sistema.cursos.keys()))

    # ----------------------
    # Acciones de login
    # ----------------------
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
            self.usuario_logueado = u
            self.etiqueta_usuario.configure(text=f"Usuario: {u}")
            self.boton_logout.configure(state="normal")
            self.mensaje_login.configure(text="Inicio correcto", text_color="green")
            self.entrada_usuario_login.delete(0, "end")
            self.entrada_pass_login.delete(0, "end")
            self.mostrar_cursos()
        else:
            self.mensaje_login.configure(text="Usuario/contraseña incorrectos", text_color="red")

    def logout(self):
        self.usuario_logueado = None
        self.etiqueta_usuario.configure(text="Sin sesión")
        self.boton_logout.configure(state="disabled")
        messagebox.showinfo("Logout", "Sesión cerrada.")
        self.mostrar_login()

    def verificar_logueo(self) -> bool:
        if not self.usuario_logueado:
            messagebox.showwarning("No autenticado", "Inicia sesión primero.")
            return False
        return True

    # ----------------------
    # Helpers UI Cursos
    # ----------------------
    def refrescar_lista_cursos(self):
        self.listbox_cursos.delete(0, "end")
        for codigo, c in sorted(self.sistema.cursos.items()):
            self.listbox_cursos.insert("end", f"{codigo} - {c.nombre} ({c.horario})")

    def llenar_formulario_curso(self, event=None):
        sel = self.listbox_cursos.curselection()
        if not sel:
            return
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        c = self.sistema.cursos.get(codigo)
        if not c:
            return
        self.entrada_codigo_curso.delete(0, "end")
        self.entrada_nombre_curso.delete(0, "end")
        self.entrada_horario_curso.delete(0, "end")
        self.entrada_codigo_curso.insert(0, c.codigo)
        self.entrada_nombre_curso.insert(0, c.nombre)
        self.entrada_horario_curso.insert(0, c.horario)

    def ui_crear_curso(self):
        codigo = self.entrada_codigo_curso.get().strip()
        nombre = self.entrada_nombre_curso.get().strip()
        horario = self.entrada_horario_curso.get().strip()
        if not codigo or not nombre:
            messagebox.showwarning("Faltan datos", "Código y nombre obligatorios.")
            return
        try:
            self.sistema.crear_curso(codigo, nombre, horario)
            messagebox.showinfo("Éxito", "Curso creado.")
            self.refrescar_lista_cursos()
        except ValueError as e:
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
            self.refrescar_lista_cursos()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_curso(self):
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
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # ----------------------
    # Helpers UI Alumnos (globales)
    # ----------------------
    def refrescar_lista_alumnos(self):
        self.listbox_alumnos.delete(0, "end")
        for sid, st in sorted(self.sistema.estudiantes.items()):
            self.listbox_alumnos.insert("end", f"{sid}: {st.nombre} (RUT: {st.rut})")

    def ui_agregar_alumno(self):
        nombre = self.entrada_nombre_alumno.get().strip()
        rut = self.entrada_rut_alumno.get().strip()
        if not nombre:
            messagebox.showwarning("Faltan datos", "Nombre obligatorio.")
            return
        st = self.sistema.agregar_estudiante_global(nombre, rut)
        messagebox.showinfo("Éxito", f"Alumno agregado (ID: {st.id}). Está en todas las clases.")
        self.entrada_nombre_alumno.delete(0, "end")
        self.entrada_rut_alumno.delete(0, "end")
        self.refrescar_lista_alumnos()

    def ui_editar_alumno(self):
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
            self.refrescar_lista_alumnos()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_alumno(self):
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
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # ----------------------
    # Helpers UI Sesiones
    # ----------------------
    def on_cambio_curso_sesiones(self, val):
        # poblar lista de alumnos multi-select y lista de sesiones
        self.listbox_alumnos_sesiones.delete(0, "end")
        self.listbox_sesiones.delete(0, "end")
        if not val:
            return
        # alumnos = estudiantes globales (aparecen en todos los cursos)
        for sid, st in sorted(self.sistema.estudiantes.items()):
            self.listbox_alumnos_sesiones.insert("end", f"{sid}: {st.nombre} (RUT: {st.rut})")
        # sesiones:
        sesiones = self.sistema.obtener_sesiones_por_curso(val)
        for s in sorted(sesiones, key=lambda x: x.fecha, reverse=True):
            self.listbox_sesiones.insert("end", f"{s.id} - {s.fecha.strftime('%Y-%m-%d %H:%M')} | Presentes: {len(s.ids_presentes)}")

    def ui_iniciar_sesion(self):
        codigo_curso = self.combo_curso_sesiones.get()
        if not codigo_curso:
            messagebox.showwarning("Seleccione curso", "Seleccione un curso primero.")
            return
        try:
            s = self.sistema.iniciar_sesion(codigo_curso)
            messagebox.showinfo("Éxito", f"Sesión {s.id} creada.")
            self.on_cambio_curso_sesiones(codigo_curso)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_marcar_presentes_seleccionados(self):
        # seleccionar sesión
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        # alumnos seleccionados (multi)
        sels = self.listbox_alumnos_sesiones.curselection()
        if not sels:
            messagebox.showwarning("Seleccione alumnos", "Seleccione uno o más alumnos.")
            return
        sids = [int(self.listbox_alumnos_sesiones.get(i).split(":")[0]) for i in sels]
        try:
            self.sistema.marcar_presentes_multiple(sess_id, sids)
            messagebox.showinfo("Éxito", f"Marcados {len(sids)} presentes en sesión {sess_id}.")
            self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_presentes_sesion(self):
        # abrir un diálogo para editar presentes de la sesión seleccionada
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión para editar.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        sess = self.sistema.sesiones.get(sess_id)
        if not sess:
            messagebox.showerror("Error", "Sesión no encontrada")
            return

        # Toplevel con checkboxes para todos los estudiantes globales
        top = tk.Toplevel(self)
        top.title(f"Editar asistentes - Sesión {sess_id}")
        top.geometry("400x500")
        tk.Label(top, text=f"Sesión {sess.id} - {sess.fecha.strftime('%Y-%m-%d %H:%M')} (Curso: {sess.codigo_curso})").pack(pady=6)
        frame = tk.Frame(top)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        # almacenar mapping de variables
        var_map = {}
        for sid, st in sorted(self.sistema.estudiantes.items()):
            var = tk.IntVar(value=1 if sid in sess.ids_presentes else 0)
            cb = tk.Checkbutton(frame, text=f"{sid}: {st.nombre}", variable=var)
            cb.pack(anchor="w")
            var_map[sid] = var

        def aplicar_cambios():
            nuevos_presentes = [sid for sid, var in var_map.items() if var.get() == 1]
            try:
                self.sistema.editar_sesion(sess_id, nuevos_ids_presentes=nuevos_presentes)
                messagebox.showinfo("Éxito", "Presentes actualizados.")
                top.destroy()
                # refrescar vista de sesiones
                self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        tk.Button(top, text="Guardar cambios", command=aplicar_cambios).pack(pady=8)
        tk.Button(top, text="Cancelar", command=top.destroy).pack(pady=4)

    def ui_eliminar_sesion(self):
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
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # ----------------------
    # UI Porcentajes
    # ----------------------
    def refrescar_lista_porcentajes(self, val):
        self.listbox_porcentajes.delete(0, "end")
        codigo_curso = self.combo_curso_porcentajes.get()
        if not codigo_curso:
            return
        for sid, st in sorted(self.sistema.estudiantes.items()):
            pct = self.sistema.porcentaje_asistencia_por_estudiante(codigo_curso, sid)
            self.listbox_porcentajes.insert("end", f"{sid}: {st.nombre} — {pct:.1f}%")

# Ejecutar
def main():
    sistema = SistemaAsistencia()
    app = AppGUI(sistema)
    app.mainloop()

if __name__ == "__main__":
    main()
