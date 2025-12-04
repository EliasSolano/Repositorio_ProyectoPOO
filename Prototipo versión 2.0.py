from __future__ import annotations
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import hashlib
import secrets # Para generar salt

# --- Configuración de Archivos ---
ARCHIVO_DATOS = "datos.json" # Guarda datos (alumnos, cursos, sesiones) POR USUARIO
ARCHIVO_USUARIOS = "usuarios.json" # Guarda datos de inicio de sesión (hash, salt, id)

# --- Funciones de Utilidad ---

def validar_rut(rut: str) -> bool:
    """
    Valida el formato del RUT chileno.
    Rechaza el RUT si contiene espacios en el input original.
    """
    # 0. NUEVA VALIDACIÓN: Rechazar cualquier espacio en el input original
    if ' ' in rut:
        return False # Rechaza RUTs con espacios
        
    # 1. Limpiar el RUT (deja solo números y 'K'/'k')
    # Esto elimina cualquier punto o guión que el usuario haya ingresado.
    rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()
    
    # 2. Validar el patrón estricto: 7 u 8 dígitos y luego un dígito o K. Total 8 o 9 caracteres.
    if not re.match(r'^\d{7,8}[0-9K]$', rut_limpio):
        return False
        
    return True

def hash_password(password: str, salt: Optional[str] = None) -> (str, str):
    """Genera un hash seguro para la contraseña."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Usamos SHA-256 para el hashing
    hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed_password, salt


# --- Clases de Datos ---
class Estudiante:
    def __init__(self, rut: str, nombre: str):
        self.rut = rut
        self.nombre = nombre

    def to_dict(self) -> Dict[str, Any]:
        return {"rut": self.rut, "nombre": self.nombre}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Estudiante":
        return Estudiante(d["rut"], d["nombre"])


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
    def __init__(self, id: int, codigo_curso: str, fecha: datetime, ruts_presentes: List[str]):
        self.id = id
        self.codigo_curso = codigo_curso
        self.fecha = fecha
        self.ruts_presentes = ruts_presentes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "codigo_curso": self.codigo_curso,
            "fecha": self.fecha.isoformat(),
            "ruts_presentes": self.ruts_presentes
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Sesion":
        return Sesion(d["id"], d["codigo_curso"], datetime.fromisoformat(d["fecha"]),
                      d.get("ruts_presentes", []))


# --- Sistema de Asistencia (Lógica Central) ---
class SistemaAsistencia:
    def __init__(self, archivo_datos: str = ARCHIVO_DATOS, archivo_usuarios: str = ARCHIVO_USUARIOS):
        super().__init__()
        self.archivo_datos = archivo_datos
        self.archivo_usuarios = archivo_usuarios

        # usuarios: rut_usuario -> {id, password_hash, salt}
        self.usuarios: Dict[str, Dict[str, Any]] = {} 
        # datos_por_usuario: user_id (int) -> {estudiantes: Dict, cursos: Dict, sesiones: Dict, siguiente_id_sesion: int}
        self.datos_por_usuario: Dict[int, Dict[str, Any]] = {} 
        self.siguiente_id_global = 1 # Para asignar IDs a nuevos usuarios

        self.cargar_todo()

    
    def cargar_todo(self):
        """
        Carga datos de usuarios y datos específicos (cursos/alumnos/sesiones).
        Asume solo la estructura de datos más reciente (keyed por user_id).
        """
        # 1. Carga de usuarios
        if not os.path.exists(self.archivo_usuarios):
            self._guardar_usuarios()
            
        with open(self.archivo_usuarios, "r", encoding="utf-8") as f:
            try:
                self.usuarios = json.load(f)
                # Calcular el siguiente ID global
                self.siguiente_id_global = max([u["id"] for u in self.usuarios.values()], default=0) + 1
            except json.JSONDecodeError:
                self.usuarios = {}
                self.siguiente_id_global = 1
        
        # 2. Carga de datos por usuario (estudiantes, cursos, sesiones) - Solo estructura por ID
        if not os.path.exists(self.archivo_datos):
            self.datos_por_usuario = {}
        else:
            with open(self.archivo_datos, "r", encoding="utf-8") as f:
                try:
                    raw_datos = json.load(f)
                    self.datos_por_usuario = {}
                    
                    if isinstance(raw_datos, dict):
                        for user_id_str, user_data in raw_datos.items():
                            try:
                                user_id = int(user_id_str)
                            except ValueError:
                                continue 
                            
                            # Reconstruir objetos de Estudiante, Curso y Sesion
                            estudiantes = {st["rut"]: Estudiante.from_dict(st) for st in user_data.get("estudiantes", [])}
                            cursos = {co["codigo"]: Curso.from_dict(co) for co in user_data.get("cursos", [])}
                            sesiones = {sess["id"]: Sesion.from_dict(sess) for sess in user_data.get("sesiones", [])}
                            
                            self.datos_por_usuario[user_id] = {
                                "estudiantes": estudiantes,
                                "cursos": cursos,
                                "sesiones": sesiones,
                                "siguiente_id_sesion": user_data.get("siguiente_id_sesion", 1)
                            }
                    
                except json.JSONDecodeError:
                    self.datos_por_usuario = {}
    
    # --- Métodos de Guardado ---
    def _guardar_datos(self):
        datos_serializables = {}
        for user_id, data in self.datos_por_usuario.items():
            datos_serializables[str(user_id)] = { 
                "estudiantes": [s.to_dict() for s in data["estudiantes"].values()],
                "cursos": [c.to_dict() for c in data["cursos"].values()],
                "sesiones": [s.to_dict() for s in data["sesiones"].values()],
                "siguiente_id_sesion": data["siguiente_id_sesion"]
            }
        
        with open(self.archivo_datos, "w", encoding="utf-8") as f:
            json.dump(datos_serializables, f, ensure_ascii=False, indent=2)

    def _guardar_usuarios(self):
        with open(self.archivo_usuarios, "w", encoding="utf-8") as f:
            json.dump(self.usuarios, f, ensure_ascii=False, indent=2)
    
    def guardar_todo(self):
        self._guardar_datos()
        self._guardar_usuarios()
    
    # --- Métodos de acceso a datos por usuario ---
    def _obtener_datos_usuario(self, user_id: int) -> Dict[str, Any]:
        """Obtiene y/o inicializa el diccionario de datos para un user_id específico."""
        if user_id not in self.datos_por_usuario:
             self.datos_por_usuario[user_id] = {
                "estudiantes": {},
                "cursos": {},
                "sesiones": {},
                "siguiente_id_sesion": 1
            }
        return self.datos_por_usuario[user_id]
    
    # --- Métodos de Usuario (login/registro) ---
    def registrar_usuario(self, rut: str, password: str) -> int:
        
        # 1. Validar y limpiar RUT
        if not validar_rut(rut):
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), y no debe contener espacios.") 
            
        rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()

        if rut_limpio in self.usuarios:
            raise ValueError("Este RUT ya está registrado para iniciar sesión.")

        # 2. Validación: Verificar que el RUT no esté registrado como alumno en NINGÚN usuario.
        for data in self.datos_por_usuario.values():
            if rut_limpio in data["estudiantes"]:
                 raise ValueError("Este RUT está registrado como alumno y no puede ser usado para iniciar sesión.")

        # 3. Validar contraseña
        if " " in password:
            raise ValueError("La contraseña no puede contener espacios.")
        if not (6 <= len(password) <= 20):
            raise ValueError("La contraseña debe tener entre 6 y 20 caracteres.")
            
        # 4. Generar hash y guardar
        password_hash, salt = hash_password(password)
        
        uid = self.siguiente_id_global
        self.usuarios[rut_limpio] = {"id": uid, "password_hash": password_hash, "salt": salt} # Clave es el RUT
        self.siguiente_id_global += 1
        
        # Inicializar datos vacíos para el nuevo usuario
        self._obtener_datos_usuario(uid) 
        
        self._guardar_usuarios()
        return uid # Retorna el ID del nuevo usuario

    def verificar_usuario(self, rut: str, password: str) -> Optional[int]:
        rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper() # Limpia el RUT de entrada
        u = self.usuarios.get(rut_limpio)
        if not u:
            return None 
        
        stored_hash = u.get("password_hash")
        salt = u.get("salt")
        
        if not stored_hash or not salt:
            return None 
            
        check_hash, _ = hash_password(password, salt)
        
        if stored_hash == check_hash:
            return u["id"] # Login exitoso, retorna el ID de usuario
        else:
            return None 

    # --- Métodos de Estudiante (necesitan user_id) ---
    def agregar_estudiante(self, user_id: int, nombre: str, rut: str) -> Estudiante:
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        
        # Validaciones
        if not nombre or not rut:
             raise ValueError("Nombre y RUT son obligatorios.")
             
        if not validar_rut(rut):
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), y no debe contener espacios.") 
            
        rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()

        if rut_limpio in estudiantes:
            raise ValueError("RUT ya existe para este usuario.")
            
        # Validación: Verificar que el RUT no esté registrado como usuario (login)
        if rut_limpio in self.usuarios:
            raise ValueError("Este RUT ya está registrado para iniciar sesión y no puede ser usado como alumno.")
            
        # Validar nombre/apellido único
        if nombre.lower().strip() in [st.nombre.lower().strip() for st in estudiantes.values()]:
            raise ValueError("Ya existe un estudiante con este nombre y apellido.")
            
        st = Estudiante(rut_limpio, nombre) 
        estudiantes[st.rut] = st
        self._guardar_datos()
        return st

    def actualizar_estudiante(self, user_id: int, rut_antiguo: str, nuevo_nombre: str, nuevo_rut: str) -> Estudiante:
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        sesiones = datos["sesiones"]
        
        # Validaciones
        if not nuevo_nombre or not nuevo_rut:
             raise ValueError("Nombre y nuevo RUT son obligatorios.")
             
        if not validar_rut(nuevo_rut):
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), y no debe contener espacios.") 
            
        nuevo_rut_limpio = re.sub(r'[^0-9kK]', '', nuevo_rut).upper()
             
        st = estudiantes.get(rut_antiguo)
        if not st:
            raise ValueError("Alumno no encontrado.")
        
        if nuevo_rut_limpio != rut_antiguo and nuevo_rut_limpio in estudiantes:
            raise ValueError("Nuevo RUT ya existe para este usuario.")
            
        # Validación: Verificar que el nuevo RUT no esté registrado como usuario (login)
        if nuevo_rut_limpio != rut_antiguo and nuevo_rut_limpio in self.usuarios:
            raise ValueError("Nuevo RUT ya está registrado para iniciar sesión y no puede ser usado como alumno.")
        
        if nuevo_nombre.lower().strip() != st.nombre.lower().strip() and nuevo_nombre.lower().strip() in [s.nombre.lower().strip() for s in estudiantes.values()]:
            raise ValueError("Ya existe un estudiante con ese nombre y apellido.")

        # Si el RUT cambia, se elimina la entrada antigua y se crea la nueva
        if nuevo_rut_limpio != rut_antiguo:
            del estudiantes[rut_antiguo]
            for sess in sesiones.values():
                if rut_antiguo in sess.ruts_presentes:
                    sess.ruts_presentes.remove(rut_antiguo)
                    sess.ruts_presentes.append(nuevo_rut_limpio) # Actualiza las sesiones
        
        st.nombre = nuevo_nombre
        st.rut = nuevo_rut_limpio
        estudiantes[nuevo_rut_limpio] = st
        self._guardar_datos()
        return st

    def eliminar_estudiante(self, user_id: int, rut: str):
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        sesiones = datos["sesiones"]
        
        if rut not in estudiantes:
            raise ValueError("Alumno no encontrado.")

        del estudiantes[rut]
        for sess in sesiones.values():
            if rut in sess.ruts_presentes:
                sess.ruts_presentes.remove(rut)
        self._guardar_datos()

    # --- Métodos de Curso (necesitan user_id) ---
    
    def crear_curso(self, user_id: int, codigo: str, nombre: str, horario: str = "") -> Curso:
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]

        if not codigo or not nombre:
             raise ValueError("Código y nombre son obligatorios.")

        if codigo in cursos:
            raise ValueError("Código de curso ya existe.")
        if nombre.lower().strip() in [c.nombre.lower().strip() for c in cursos.values()]:
            raise ValueError("Ya existe un curso con este nombre.")

        co = Curso(codigo, nombre, horario)
        cursos[codigo] = co
        self._guardar_datos()
        return co

    def actualizar_curso(self, user_id: int, codigo_antiguo: str, codigo_nuevo: str, nombre: str, horario: str) -> Curso:
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        sesiones = datos["sesiones"]
        
        if not codigo_nuevo or not nombre:
             raise ValueError("Código y nombre son obligatorios.")

        if codigo_antiguo not in cursos:
            raise ValueError("Curso no encontrado.")
        if codigo_nuevo != codigo_antiguo and codigo_nuevo in cursos:
            raise ValueError("Nuevo código ya existe.")
            
        curso_actual = cursos.get(codigo_antiguo)
        if nombre.lower().strip() != curso_actual.nombre.lower().strip() and nombre.lower().strip() in [c.nombre.lower().strip() for c in cursos.values()]:
            raise ValueError("Ya existe un curso con este nombre.")

        co = cursos.pop(codigo_antiguo)
        co.codigo = codigo_nuevo
        co.nombre = nombre
        co.horario = horario
        cursos[codigo_nuevo] = co
        for s in sesiones.values():
            if s.codigo_curso == codigo_antiguo:
                s.codigo_curso = codigo_nuevo
        self._guardar_datos()
        return co

    def eliminar_curso(self, user_id: int, codigo: str):
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        sesiones = datos["sesiones"]
        
        if codigo not in cursos:
            raise ValueError("Curso no encontrado.")
        del cursos[codigo]
        datos["sesiones"] = {sid: s for sid, s in sesiones.items() if s.codigo_curso != codigo}
        self.datos_por_usuario[user_id]["sesiones"] = datos["sesiones"]
        self._guardar_datos()

    # --- Métodos de Sesión (necesitan user_id) ---
    
    def iniciar_sesion(self, user_id: int, codigo_curso: str) -> Sesion:
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        sesiones = datos["sesiones"]
        siguiente_id_sesion = datos["siguiente_id_sesion"]
        
        if codigo_curso not in cursos:
            raise ValueError("Curso no encontrado.")
        sess = Sesion(siguiente_id_sesion, codigo_curso, datetime.now(), []) 
        sesiones[sess.id] = sess
        datos["siguiente_id_sesion"] += 1
        self._guardar_datos()
        return sess

    def editar_sesion(self, user_id: int, sesion_id: int, nueva_fecha: Optional[datetime] = None, nuevos_ruts_presentes: Optional[List[str]] = None):
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        sesiones = datos["sesiones"]
        
        sess = sesiones.get(sesion_id)
        if not sess:
            raise ValueError("Sesión no encontrada.")
        if nueva_fecha:
            sess.fecha = nueva_fecha
        if nuevos_ruts_presentes is not None: 
            ruts_validos = set(estudiantes.keys())
            sess.ruts_presentes = [rut for rut in nuevos_ruts_presentes if rut in ruts_validos]
        self._guardar_datos()

    def eliminar_sesion(self, user_id: int, sesion_id: int):
        datos = self._obtener_datos_usuario(user_id)
        sesiones = datos["sesiones"]
        
        if sesion_id not in sesiones:
            raise ValueError("Sesión no encontrada.")
        del sesiones[sesion_id]
        self._guardar_datos()

    def obtener_sesiones_por_curso(self, user_id: int, codigo_curso: str) -> List[Sesion]:
        datos = self._obtener_datos_usuario(user_id)
        return [s for s in datos["sesiones"].values() if s.codigo_curso == codigo_curso]


    def porcentaje_asistencia_por_estudiante(self, user_id: int, codigo_curso: str, rut_estudiante: str) -> float:
        sesiones_usuario = self.obtener_sesiones_por_curso(user_id, codigo_curso)
        if not sesiones_usuario:
            return 0.0
        asistido = sum(1 for s in sesiones_usuario if rut_estudiante in s.ruts_presentes) 
        return (asistido / len(sesiones_usuario)) * 100.0

def toggle_password(self):
    if self.entrada_pass_login.cget("show") == "*":
        self.entrada_pass_login.configure(show="")
        self.btn_toggle.configure(text="Ocultar contraseña")
    else:
        self.entrada_pass_login.configure(show="*")
        self.btn_toggle.configure(text="Mostrar contraseña")

# --- GUI (Interfaz del customtkinter) ---
class AppGUI(ctk.CTk):
    def __init__(self, sistema: SistemaAsistencia):
        super().__init__()
        self.sistema = sistema
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("Sistema de Asistencia para Profesores")
        ctk.set_widget_scaling(0.9)
        self.geometry("1280x720")

        self.usuario_logueado: Optional[str] = None 
        self.user_id: Optional[int] = None 
        
        # Variables de estado para edición (Clave para mantener la referencia al editar)
        self.rut_seleccionado_actual: Optional[str] = None
        self.codigo_seleccionado_actual: Optional[str] = None

        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=10, pady=8)
        self.etiqueta_titulo = ctk.CTkLabel(header, text="Sistema de Asistencia para Profesores", font=("Arial", 24, "bold"))
        self.etiqueta_titulo.pack(side="left", padx=10)
        self.etiqueta_usuario = ctk.CTkLabel(header, text="Sin sesión", font=("Arial", 24))
        self.etiqueta_usuario.pack(side="right", padx=10)
        self.boton_logout = ctk.CTkButton(header, text="Cerrar sesion", command=self.logout, state="disabled", font=("Arial", 24))
        self.boton_logout.pack(side="right", padx=10)

        nav = ctk.CTkFrame(self)
        nav.pack(side="top", fill="x", padx=10, pady=8)
        self.btn_vista_login = ctk.CTkButton(nav, text="Login", command=self.mostrar_login_frame, font=("Arial", 24))
        self.btn_vista_cursos = ctk.CTkButton(nav, text="Cursos", command=self.mostrar_cursos, state="disabled", font=("Arial", 24))
        self.btn_vista_alumnos = ctk.CTkButton(nav, text="Alumnos", command=self.mostrar_alumnos, state="disabled", font=("Arial", 24))
        self.btn_vista_sesiones = ctk.CTkButton(nav, text="Sesiones", command=self.mostrar_sesiones, state="disabled", font=("Arial", 24))
        self.btn_vista_porcentajes = ctk.CTkButton(nav, text="Porcentajes", command=self.mostrar_porcentajes, state="disabled", font=("Arial", 24))
        for b in (self.btn_vista_login, self.btn_vista_cursos, self.btn_vista_alumnos, self.btn_vista_sesiones, self.btn_vista_porcentajes):
            b.pack(side="left", padx=8, pady=4)

        self.contenido = ctk.CTkFrame(self)
        self.contenido.pack(side="top", fill="both", expand=True, padx=10, pady=8)

        self.frame_login = self.construir_frame_login()
        self.frame_cursos = None
        self.frame_alumnos = None
        self.frame_sesiones = None
        self.frame_porcentajes = None

        self.mostrar_login_frame() 

    def actualizar_botones_nav(self, estado: str):
        """Actualiza el estado de los botones de navegación (normal o disabled)."""
        for b in (self.btn_vista_cursos, self.btn_vista_alumnos, self.btn_vista_sesiones, self.btn_vista_porcentajes):
            b.configure(state=estado)
        self.boton_logout.configure(state=estado)
        
        if estado == "normal":
             self.btn_vista_login.configure(state="disabled") 
        else: 
             self.btn_vista_login.configure(state="normal") 

    import tkinter as tk  # asegúrate de tener este import al inicio del archivo

    def construir_frame_login(self):
        frm = ctk.CTkFrame(self.contenido)

        lbl = ctk.CTkLabel(frm, text="Iniciar sesión o registrarse", font=("Arial", 40, "bold"))
        lbl.pack(pady=20)

        ctk.CTkLabel(frm, text="RUT (Ejemplo: 22152895K, sin puntos, ni guion)", font=("Arial", 25)).pack(pady=4)
        self.entrada_rut_login = ctk.CTkEntry(frm, width=300, font=("Arial", 20))
        self.entrada_rut_login.pack(pady=10)

        ctk.CTkLabel(frm, text="Contraseña (de 6 a 20 caracteres, sin espacios)", font=("Arial", 25)).pack(pady=4)
        self.entrada_pass_login = ctk.CTkEntry(frm, width=300, font=("Arial", 20), show="*")
        self.entrada_pass_login.pack(pady=10)

        # Botón que llama a un método de la clase y usa textvariable
        self.toggle_text = tk.StringVar(value="Mostrar contraseña")
        self.btn_toggle = ctk.CTkButton(frm, textvariable=self.toggle_text, command=self.toggle_password, font=("Arial", 18))
        self.btn_toggle.pack(pady=5)

        # Botones de acción
        btn_login = ctk.CTkButton(frm, text="Iniciar sesión", command=self.accion_login, font=("Arial", 27))
        btn_register = ctk.CTkButton(frm, text="Registrarse", command=self.accion_registrar, font=("Arial", 27))
        btn_login.pack(pady=10)
        btn_register.pack(pady=10)

        self.mensaje_login = ctk.CTkLabel(frm, text="")
        self.mensaje_login.pack(pady=10)

        return frm

    def toggle_password(self):
        if self.entrada_pass_login.cget("show") == "*":
            self.entrada_pass_login.configure(show="")
            self.toggle_text.set("Ocultar contraseña")
        else:
            self.entrada_pass_login.configure(show="*")
            self.toggle_text.set("Mostrar contraseña")

    def construir_frame_cursos(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Crear / Modificar Cursos", font=("Arial", 30, "bold")).pack(side="left", padx=10)

        campos = ctk.CTkFrame(frm)
        campos.pack(side="top", fill="x", padx=10, pady=10)
        
        input_frame = ctk.CTkFrame(campos)
        input_frame.pack(pady=5)
        
        ctk.CTkLabel(input_frame, text="Código (ej: CS101):", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_codigo_curso = ctk.CTkEntry(input_frame)
        self.entrada_codigo_curso.pack(side="left", padx=10)
        
        ctk.CTkLabel(input_frame, text="Nombre (ej: Cálculo):", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_nombre_curso = ctk.CTkEntry(input_frame)
        self.entrada_nombre_curso.pack(side="left", padx=10)
        
        ctk.CTkLabel(input_frame, text="Horario:", font=("Arial",20)).pack(side="left", padx=10)
        self.entrada_horario_curso = ctk.CTkEntry(input_frame)
        self.entrada_horario_curso.pack(side="left", padx=10)

        btns = ctk.CTkFrame(campos)
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Crear Curso", command=self.ui_crear_curso, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Editar seleccionado", command=self.ui_editar_curso, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Borrar seleccionado", command=self.ui_eliminar_curso, font=("Arial", 22)).pack(side="left", padx=10)

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf, text="Lista de Cursos:", font=("Arial", 30, "bold")).pack(anchor="w", padx=10)
        
        # Cambio para que la selección visual persista: exportselection=False
        self.listbox_cursos = tk.Listbox(listf, height=24, font=("Arial", 24), exportselection=False)
        self.listbox_cursos.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        sb = tk.Scrollbar(listf, command=self.listbox_cursos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_cursos.config(yscrollcommand=sb.set)
        self.listbox_cursos.bind("<<ListboxSelect>>", self.llenar_formulario_curso)

        return frm

    def construir_frame_alumnos(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Alumnos", font=("Arial", 30, "bold")).pack(side="left", padx=10)

        campos = ctk.CTkFrame(frm)
        campos.pack(side="top", fill="x", padx=10, pady=10)
        
        input_frame = ctk.CTkFrame(campos)
        input_frame.pack(pady=5)
        
        ctk.CTkLabel(input_frame, text="Nombre completo (ej: Agustin Vejar):", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_nombre_alumno = ctk.CTkEntry(input_frame)
        self.entrada_nombre_alumno.pack(side="left", padx=10)
        
        ctk.CTkLabel(input_frame, text="RUT (ej: 21123456K):", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_rut_alumno = ctk.CTkEntry(input_frame) 
        self.entrada_rut_alumno.pack(side="left", padx=10)

        btns = ctk.CTkFrame(campos)
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Agregar Alumno", command=self.ui_agregar_alumno, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Editar seleccionado", command=self.ui_editar_alumno, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Eliminar seleccionado", command=self.ui_eliminar_alumno, font=("Arial", 22)).pack(side="left", padx=10)

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf, text="Lista de Alumnos:", font=("Arial", 30, "bold")).pack(anchor="w", padx=10)
        
        # Cambio para que la selección visual persista: exportselection=False
        self.listbox_alumnos = tk.Listbox(listf, height=24, font=("Arial", 24), exportselection=False)
        self.listbox_alumnos.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        sb = tk.Scrollbar(listf, command=self.listbox_alumnos.yview)
        sb.pack(side="right", fill="y")
        self.listbox_alumnos.config(yscrollcommand=sb.set)
        self.listbox_alumnos.bind("<<ListboxSelect>>", self.llenar_formulario_alumno) 

        return frm

    def construir_frame_sesiones(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Sesiones por curso", font=("Arial", 30, "bold")).pack(side="left", padx=10)
        
        mid = ctk.CTkFrame(frm)
        mid.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(mid, text="Seleccionar Curso:", font=("Arial", 26, "bold")).pack(side="left", padx=10)
        self.combo_curso_sesiones = ctk.CTkComboBox(mid, values=[], font=("Arial", 20)) 
        self.combo_curso_sesiones.pack(side="left", padx=10)
        self.combo_curso_sesiones.configure(command=self.on_cambio_curso_sesiones)
        
        acciones = ctk.CTkFrame(mid)
        acciones.pack(side="right", padx=10)
        ctk.CTkButton(acciones, text="Crear sesión", command=self.ui_iniciar_sesion, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(acciones, text="Editar presentes (sesión seleccionada)", command=self.ui_editar_presentes_sesion, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(acciones, text="Eliminar sesión", command=self.ui_eliminar_sesion, font=("Arial", 22)).pack(side="left", padx=10)

        leftf = ctk.CTkFrame(frm)
        leftf.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(leftf, text="Lista de Alumnos (Referencia)", font=("Arial", 22, "bold")).pack(anchor="w", padx=10)
        self.listbox_alumnos_sesiones = tk.Listbox(leftf, selectmode="extended", font=("Arial", 18))
        self.listbox_alumnos_sesiones.pack(fill="both", expand=True, padx=10, pady=10)

        rightf = ctk.CTkFrame(frm)
        rightf.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(rightf, text="Lista de Sesiones (Seleccionar una para editar)", font=("Arial", 25, "bold")).pack(anchor="w", padx=10)
        self.listbox_sesiones = tk.Listbox(rightf, height=16, font=("Arial", 20))
        self.listbox_sesiones.pack(fill="both", expand=True, padx=10, pady=10)
        self.listbox_sesiones.bind("<<ListboxSelect>>", lambda e: None)

        return frm

    def construir_frame_porcentajes(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Porcentajes de Asistencia por curso", font=("Arial", 30, "bold")).pack(side="left", padx=10)

        ctk.CTkLabel(frm, text="Seleccionar Curso:", font=("Arial", 25, "bold")).pack(padx=10, pady=10, anchor="w")
        self.combo_curso_porcentajes = ctk.CTkComboBox(frm, values=[], font=("Arial", 22))
        self.combo_curso_porcentajes.pack(padx=10, pady=6, anchor="w")
        self.combo_curso_porcentajes.configure(command=self.refrescar_lista_porcentajes)

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf, text="Asistencia por Alumno:", font=("Arial", 25, "bold")).pack(anchor="w", padx=10)
        self.listbox_porcentajes = tk.Listbox(listf, font=("Arial", 22))
        self.listbox_porcentajes.pack(fill="both", expand=True, padx=10, pady=10)

        return frm
    
    # Mostrar frames
    def limpiar_contenido(self):
        for w in self.contenido.winfo_children():
            w.pack_forget()

    def mostrar_login_frame(self):
        """Muestra el frame de login/registro. Si ya está logueado, redirige a cursos."""
        if self.user_id is not None:
            self.mostrar_cursos()
            return
            
        self.limpiar_contenido()
        self.frame_login.pack(fill="both", expand=True)

    def verificar_logueo(self) -> bool:
        if not self.usuario_logueado or self.user_id is None:
            messagebox.showwarning("No autenticado", "Inicia sesión primero.")
            self.etiqueta_usuario.configure(text="Sin sesión")
            self.actualizar_botones_nav("disabled")
            self.mostrar_login_frame()
            return False
        return True

    def mostrar_cursos(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_cursos:
            self.frame_cursos = self.construir_frame_cursos()
        self.frame_cursos.pack(fill="both", expand=True)
        self.refrescar_lista_cursos()
        # Asegurarse de limpiar la variable de selección al cambiar de vista
        self.codigo_seleccionado_actual = None 

    def mostrar_alumnos(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_alumnos:
            self.frame_alumnos = self.construir_frame_alumnos()
        self.frame_alumnos.pack(fill="both", expand=True)
        self.refrescar_lista_alumnos()
        # Asegurarse de limpiar la variable de selección al cambiar de vista
        self.rut_seleccionado_actual = None

    def mostrar_sesiones(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_sesiones:
            self.frame_sesiones = self.construir_frame_sesiones()
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        cursos_keys = list(datos_usuario.get("cursos", {}).keys())
        self.combo_curso_sesiones.configure(values=cursos_keys)
        if cursos_keys:
            self.combo_curso_sesiones.set(cursos_keys[0])
            self.on_cambio_curso_sesiones(cursos_keys[0])
        else:
            self.combo_curso_sesiones.set("")
            self.on_cambio_curso_sesiones("") 
            
        self.frame_sesiones.pack(fill="both", expand=True)

    def mostrar_porcentajes(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_porcentajes:
            self.frame_porcentajes = self.construir_frame_porcentajes()
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        cursos_keys = list(datos_usuario.get("cursos", {}).keys())
        self.combo_curso_porcentajes.configure(values=cursos_keys)
        if cursos_keys:
            self.combo_curso_porcentajes.set(cursos_keys[0])
            self.refrescar_lista_porcentajes(cursos_keys[0])
        else:
            self.combo_curso_porcentajes.set("")
            self.listbox_porcentajes.delete(0, "end")
            
        self.frame_porcentajes.pack(fill="both", expand=True)

    # Login/Registro
    def accion_registrar(self):
        rut = self.entrada_rut_login.get().strip() 
        p = self.entrada_pass_login.get().strip()
        try:
            self.sistema.registrar_usuario(rut, p) 
            messagebox.showinfo("Registro exitoso", "Usuario creado con exito. Inicia sesión.")
            self.entrada_pass_login.delete(0, "end")
        except ValueError as e:
            messagebox.showerror("Error de Registro", str(e))
            self.mensaje_login.configure(text="") # Limpiar mensaje de éxito previo

    def accion_login(self):
        rut = self.entrada_rut_login.get().strip() 
        p = self.entrada_pass_login.get().strip()
        
        # Validación de espacios explícita para la entrada de login, ya que validar_rut lo rechaza
        if ' ' in rut:
            messagebox.showerror("Error de Autenticación", "El RUT no debe contener espacios.")
            self.mensaje_login.configure(text="")
            return

        # Validación general del RUT antes de verificar
        if not validar_rut(rut):
            messagebox.showerror("Error de Autenticación", "Formato de RUT incorrecto.")
            self.mensaje_login.configure(text="")
            return

        user_id = self.sistema.verificar_usuario(rut, p) 
        
        if user_id is not None:
            # Si el login es exitoso, el RUT limpio se toma como identificador
            rut_limpio_input = re.sub(r'[^0-9kK]', '', rut).upper()
            self.usuario_logueado = rut_limpio_input
            self.user_id = user_id
            self.etiqueta_usuario.configure(text=f"RUT: {self.usuario_logueado}") 
            self.actualizar_botones_nav("normal") 
            self.mensaje_login.configure(text="Inicio correcto", text_color="green")
            self.entrada_rut_login.delete(0, "end")
            self.entrada_pass_login.delete(0, "end")
            self.mostrar_cursos()
        else:
            messagebox.showerror("Error de Autenticación", "RUT o contraseña incorrectos.") 
            self.mensaje_login.configure(text="") # Limpiar mensaje de éxito previo

    def logout(self):
        self.usuario_logueado = None
        self.user_id = None
        messagebox.showinfo("Logout", "Sesión cerrada.")
        self.etiqueta_usuario.configure(text="Sin sesión")
        self.actualizar_botones_nav("disabled") 
        self.mostrar_login_frame() 

    # Cursos
    def refrescar_lista_cursos(self):
        if not self.verificar_logueo(): return
        self.listbox_cursos.delete(0, "end")
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        for codigo, c in sorted(datos_usuario.get("cursos", {}).items()):
            self.listbox_cursos.insert("end", f"{codigo} - {c.nombre} ({c.horario})")
        self.codigo_seleccionado_actual = None 

    def llenar_formulario_curso(self, event=None):
        sel = self.listbox_cursos.curselection()
        if not sel or not self.verificar_logueo():
            self.codigo_seleccionado_actual = None 
            return
        
        # Obtener el texto del elemento seleccionado
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        c = datos_usuario.get("cursos", {}).get(codigo)
        
        if not c:
            self.codigo_seleccionado_actual = None
            return
        
        # IMPORTANTE: Guardar el código seleccionado antes de que se pierda el foco
        self.codigo_seleccionado_actual = c.codigo
        
        # Llenar el formulario
        self.entrada_codigo_curso.delete(0, "end")
        self.entrada_nombre_curso.delete(0, "end")
        self.entrada_horario_curso.delete(0, "end")
        self.entrada_codigo_curso.insert(0, c.codigo)
        self.entrada_nombre_curso.insert(0, c.nombre)
        self.entrada_horario_curso.insert(0, c.horario)

    def ui_crear_curso(self):
        if not self.verificar_logueo(): return
        codigo = self.entrada_codigo_curso.get().strip()
        nombre = self.entrada_nombre_curso.get().strip()
        horario = self.entrada_horario_curso.get().strip()
        try:
            self.sistema.crear_curso(self.user_id, codigo, nombre, horario)
            messagebox.showinfo("Éxito", "Curso creado.")
            self.refrescar_lista_cursos()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_curso(self):
        if not self.verificar_logueo(): return
        
        # Usar la variable de estado guardada
        codigo_antiguo = self.codigo_seleccionado_actual
        if not codigo_antiguo:
            messagebox.showwarning("Seleccione", "Seleccione un curso para editar (haga clic en él en la lista).")
            return
            
        codigo_nuevo = self.entrada_codigo_curso.get().strip()
        nuevo_nombre = self.entrada_nombre_curso.get().strip()
        nuevo_horario = self.entrada_horario_curso.get().strip()
        try:
            self.sistema.actualizar_curso(self.user_id, codigo_antiguo, codigo_nuevo, nuevo_nombre, nuevo_horario)
            messagebox.showinfo("Éxito", "Curso modificado.")
            self.refrescar_lista_cursos()
            self.codigo_seleccionado_actual = None 
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_curso(self):
        if not self.verificar_logueo(): return
        sel = self.listbox_cursos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un curso para eliminar.")
            return
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        if messagebox.askyesno("Confirmar", f"Eliminar curso {codigo}? Se borrarán sus sesiones."):
            try:
                self.sistema.eliminar_curso(self.user_id, codigo)
                messagebox.showinfo("Éxito", "Curso eliminado.")
                self.refrescar_lista_cursos()
                self.codigo_seleccionado_actual = None 
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # Alumnos
    def refrescar_lista_alumnos(self):
        if not self.verificar_logueo(): return
        self.listbox_alumnos.delete(0, "end")
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items()):
            self.listbox_alumnos.insert("end", f"RUT: {rut} - {st.nombre}") 
        self.rut_seleccionado_actual = None

    def llenar_formulario_alumno(self, event=None):
        sel = self.listbox_alumnos.curselection()
        if not sel or not self.verificar_logueo():
            self.rut_seleccionado_actual = None 
            return
        txt = self.listbox_alumnos.get(sel[0])
        rut = txt.split(" - ")[0].replace("RUT: ", "").strip() 
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        st = datos_usuario.get("estudiantes", {}).get(rut)
        
        if not st:
            self.rut_seleccionado_actual = None
            return
        
        # IMPORTANTE: Guardar el RUT seleccionado antes de que se pierda el foco
        self.rut_seleccionado_actual = st.rut
        
        self.entrada_nombre_alumno.delete(0, "end")
        self.entrada_rut_alumno.delete(0, "end")
        self.entrada_nombre_alumno.insert(0, st.nombre)
        self.entrada_rut_alumno.insert(0, st.rut)

    def ui_agregar_alumno(self):
        if not self.verificar_logueo(): return
        nombre = self.entrada_nombre_alumno.get().strip()
        rut = self.entrada_rut_alumno.get().strip() 
        try:
            st = self.sistema.agregar_estudiante(self.user_id, nombre, rut) 
            messagebox.showinfo("Éxito", f"Alumno agregado (RUT: {st.rut}).")
            self.entrada_nombre_alumno.delete(0, "end")
            self.entrada_rut_alumno.delete(0, "end")
            self.refrescar_lista_alumnos()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_alumno(self):
        if not self.verificar_logueo(): return
        
        # Usar la variable de estado guardada
        rut_antiguo = self.rut_seleccionado_actual
        if not rut_antiguo:
            messagebox.showwarning("Seleccione", "Seleccione un alumno para editar (haga clic en él en la lista).")
            return
            
        nuevo_nombre = self.entrada_nombre_alumno.get().strip()
        nuevo_rut = self.entrada_rut_alumno.get().strip()
            
        try:
            self.sistema.actualizar_estudiante(self.user_id, rut_antiguo, nuevo_nombre, nuevo_rut) 
            messagebox.showinfo("Éxito", "Alumno modificado.")
            self.refrescar_lista_alumnos()
            self.entrada_nombre_alumno.delete(0, "end") 
            self.entrada_rut_alumno.delete(0, "end")
            self.rut_seleccionado_actual = None 
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_eliminar_alumno(self):
        if not self.verificar_logueo(): return
        sel = self.listbox_alumnos.curselection()
        if not sel:
            messagebox.showwarning("Seleccione", "Seleccione un alumno para eliminar.")
            return
        txt = self.listbox_alumnos.get(sel[0])
        rut = txt.split(" - ")[0].replace("RUT: ", "").strip() 
        if messagebox.askyesno("Confirmar", f"Eliminar alumno con RUT {rut}? Esto lo quita de todas las sesiones."):
            try:
                self.sistema.eliminar_estudiante(self.user_id, rut)
                messagebox.showinfo("Éxito", "Alumno eliminado.")
                self.refrescar_lista_alumnos()
                self.rut_seleccionado_actual = None 
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # Sesiones
    def on_cambio_curso_sesiones(self, codigo_curso: str):
        if self.user_id is None: 
            self.listbox_alumnos_sesiones.delete(0, "end")
            self.listbox_sesiones.delete(0, "end")
            return
        if not self.verificar_logueo(): return
        
        self.listbox_alumnos_sesiones.delete(0, "end")
        self.listbox_sesiones.delete(0, "end")
        if not codigo_curso:
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
            
        # alumnos
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items()):
            self.listbox_alumnos_sesiones.insert("end", f"RUT: {rut} - {st.nombre}")
            
        # sesiones:
        try:
            sesiones = self.sistema.obtener_sesiones_por_curso(self.user_id, codigo_curso)
            for s in sorted(sesiones, key=lambda x: x.fecha, reverse=True):
                self.listbox_sesiones.insert("end", f"{s.id} - {s.fecha.strftime('%Y-%m-%d %H:%M')} | Presentes: {len(s.ruts_presentes)}") 
        except ValueError as e:
            messagebox.showerror("Error", str(e))


    def ui_iniciar_sesion(self):
        if not self.verificar_logueo(): return
        codigo_curso = self.combo_curso_sesiones.get()
        if not codigo_curso:
            messagebox.showwarning("Seleccione curso", "Seleccione un curso primero.")
            return
        try:
            s = self.sistema.iniciar_sesion(self.user_id, codigo_curso)
            messagebox.showinfo("Éxito", f"Sesión {s.id} creada.")
            self.on_cambio_curso_sesiones(codigo_curso)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def ui_editar_presentes_sesion(self):
        if not self.verificar_logueo(): return
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión para editar.")
            return
            
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        sess = datos_usuario.get("sesiones", {}).get(sess_id)
        
        if not sess:
            messagebox.showerror("Error", "Sesión no encontrada.")
            return

        top = tk.Toplevel(self)
        top.title(f"Editar asistentes - Sesión {sess_id}")
        top.geometry("1200x850")
        ctk.CTkLabel(top, text=f"Sesión {sess.id} - {sess.fecha.strftime('%Y-%m-%d %H:%M')} (Curso: {sess.codigo_curso})", font=("Arial", 28, "bold")).pack(pady=10)
        
        canvas = tk.Canvas(top)
        scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y", padx=10, pady=5)
        
        var_map = {}
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items()): 
            var = tk.IntVar(value=1 if rut in sess.ruts_presentes else 0) 
            cb = ctk.CTkCheckBox(scrollable_frame, text=f"RUT: {rut} - {st.nombre}", variable=var, font=("Arial", 22)) 
            cb.pack(anchor="w", padx=15, pady=2)
            var_map[rut] = var

        def aplicar_cambios():
            nuevos_ruts_presentes = [rut for rut, var in var_map.items() if var.get() == 1] 
            try:
                self.sistema.editar_sesion(self.user_id, sess_id, nuevos_ruts_presentes=nuevos_ruts_presentes) 
                messagebox.showinfo("Éxito", "Presentes actualizados.")
                top.destroy()
                self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(top, text="Guardar cambios", command=aplicar_cambios, font=("Arial", 26)).pack(pady=10)
        ctk.CTkButton(top, text="Cancelar", command=top.destroy, font=("Arial", 26)).pack(pady=10)

    def ui_eliminar_sesion(self):
        if not self.verificar_logueo(): return
        sel_s = self.listbox_sesiones.curselection()
        if not sel_s:
            messagebox.showwarning("Seleccione sesión", "Seleccione una sesión para eliminar.")
            return
        sess_txt = self.listbox_sesiones.get(sel_s[0])
        sess_id = int(sess_txt.split(" - ")[0])
        if messagebox.askyesno("Confirmar", f"Eliminar sesión {sess_id}?"):
            try:
                self.sistema.eliminar_sesion(self.user_id, sess_id)
                messagebox.showinfo("Éxito", "Sesión eliminada.")
                self.on_cambio_curso_sesiones(self.combo_curso_sesiones.get())
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # Porcentajes
    def refrescar_lista_porcentajes(self, val):
        if not self.verificar_logueo(): return
        self.listbox_porcentajes.delete(0, "end")
        codigo_curso = self.combo_curso_porcentajes.get()
        if not codigo_curso:
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        
        if codigo_curso not in datos_usuario.get("cursos", {}):
            return

        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items()): 
            pct = self.sistema.porcentaje_asistencia_por_estudiante(self.user_id, codigo_curso, rut) 
            self.listbox_porcentajes.insert("end", f"RUT: {rut} - {st.nombre} — {pct:.1f}%") 

def main():
    sistema = SistemaAsistencia()
    app = AppGUI(sistema)
    app.mainloop()

if __name__ == "__main__":
    main()