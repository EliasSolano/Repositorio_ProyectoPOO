from __future__ import annotations
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import hashlib
import secrets

ARCHIVO_DATOS = "datos.json" # Guarda datos (alumnos, cursos, sesiones, etc.) POR USUARIO
ARCHIVO_USUARIOS = "usuarios.json" # Guarda datos de inicio de sesión (hash, salt, id, etc.)

# Funciones de Utilidad

def validar_rut(rut: str) -> bool:
    
    if ' ' in rut:
        return False # Verifica que no hayan espacios
        
    # Esto elimina cualquier punto o guión que el usuario haya ingresado
    rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()
    
    # Valida que tenga 7 u 8 dígitos y luego un dígito o K
    if not re.match(r'^\d{7,8}[0-9K]$', rut_limpio):
        return False
        
    # **NUEVA VALIDACIÓN** - Evita RUTs repetitivos (11111111-1, 22222222-2, etc.)
    # Se considera un RUT repetitivo si todos los dígitos son iguales (antes del dígito verificador)
    parte_numerica = rut_limpio[:-1]
    if len(set(parte_numerica)) == 1:
        return False
        
    return True

def hash_password(password: str, salt: Optional[str] = None) -> (str, str):
    # Genera un hash seguro para la contraseña
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Usamos SHA-256 para el hashing
    hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed_password, salt


# Clases principales
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
    def __init__(self, codigo: str, nombre: str, horario: Optional[str] = "", estudiantes_ruts: Optional[List[str]] = None, cerrado: bool = False, min_asistencia: float = 60.0):
        self.codigo = codigo
        self.nombre = nombre
        self.horario = horario
        # **NUEVA FUNCIONALIDAD** - Estudiantes asignados al curso
        self.estudiantes_ruts = set(estudiantes_ruts) if estudiantes_ruts else set()
        # **NUEVA FUNCIONALIDAD** - Curso cerrado
        self.cerrado = cerrado
        # **NUEVA FUNCIONALIDAD** - Mínimo de asistencia
        self.min_asistencia = min_asistencia

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codigo": self.codigo, 
            "nombre": self.nombre, 
            "horario": self.horario,
            "estudiantes_ruts": list(self.estudiantes_ruts), # Guardar como lista
            "cerrado": self.cerrado,
            "min_asistencia": self.min_asistencia
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Curso":
        return Curso(
            d["codigo"], 
            d["nombre"], 
            d.get("horario", ""), 
            d.get("estudiantes_ruts"), 
            d.get("cerrado", False),
            d.get("min_asistencia", 60.0)
        )


class Sesion:
    def __init__(self, id: int, codigo_curso: str, fecha: datetime, ruts_presentes: List[str], ruts_justificados: Optional[List[str]] = None):
        self.id = id
        self.codigo_curso = codigo_curso
        self.fecha = fecha
        self.ruts_presentes = set(ruts_presentes)
        # **NUEVA FUNCIONALIDAD** - Inasistencias justificadas
        self.ruts_justificados = set(ruts_justificados) if ruts_justificados else set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "codigo_curso": self.codigo_curso,
            "fecha": self.fecha.isoformat(),
            "ruts_presentes": list(self.ruts_presentes), # Guardar como lista
            "ruts_justificados": list(self.ruts_justificados) # Guardar como lista
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Sesion":
        return Sesion(
            d["id"], 
            d["codigo_curso"], 
            datetime.fromisoformat(d["fecha"]),
            d.get("ruts_presentes", []),
            d.get("ruts_justificados", [])
        )


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
        
        # 2. Carga de datos por usuario (estudiantes, cursos, sesiones)
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
        
    def _obtener_rut_por_id(self, user_id: int) -> Optional[str]:
        """Busca el RUT asociado a un user_id."""
        for rut, u_data in self.usuarios.items():
            if u_data.get("id") == user_id:
                return rut
        return None

    # --- Métodos de Usuario (login/registro/configuración) ---
    def registrar_usuario(self, rut: str, password: str) -> int:
        
        # 1. Validar y limpiar RUT
        if not validar_rut(rut):
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), sin espacios, y no debe ser un RUT repetitivo (ej: 11.111.111-1).") 
            
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
        
    def actualizar_usuario(self, user_id: int, rut_antiguo: str, nuevo_rut: str, nueva_pass: str):
        # El llamador debe asegurar que rut_antiguo y nueva_pass/nuevo_rut son correctos.
        
        # Validar si el nuevo RUT es diferente y si es un RUT válido
        rut_limpio_antiguo = re.sub(r'[^0-9kK]', '', rut_antiguo).upper()
        rut_limpio_nuevo = re.sub(r'[^0-9kK]', '', nuevo_rut).upper()

        if rut_limpio_nuevo != rut_limpio_antiguo:
            if not validar_rut(nuevo_rut):
                raise ValueError("Nuevo RUT inválido.")
            
            # Validación: Que el nuevo RUT no exista como usuario
            if rut_limpio_nuevo in self.usuarios:
                raise ValueError("El nuevo RUT ya está registrado como usuario.")

            # Validación: Que el nuevo RUT no exista como alumno en NINGÚN usuario.
            for data in self.datos_por_usuario.values():
                if rut_limpio_nuevo in data["estudiantes"]:
                    raise ValueError("El nuevo RUT está registrado como alumno.")

        # Validar si la nueva contraseña es diferente y si es válida
        password_hash_nueva, salt_nuevo = hash_password(nueva_pass)
        
        # Re-hashear la contraseña almacenada para comparación
        stored_user = self.usuarios[rut_limpio_antiguo]
        pass_check, _ = hash_password(nueva_pass, stored_user["salt"])
        
        # La contraseña es diferente solo si el hash generado con el salt *almacenado* no coincide
        pass_es_nueva = (pass_check != stored_user["password_hash"])
        
        if pass_es_nueva:
            if " " in nueva_pass:
                raise ValueError("La contraseña no puede contener espacios.")
            if not (6 <= len(nueva_pass) <= 20):
                raise ValueError("La contraseña debe tener entre 6 y 20 caracteres.")
        else:
            # Si la contraseña es la misma, se usa el hash y salt viejos.
            password_hash_nueva = stored_user["password_hash"]
            salt_nuevo = stored_user["salt"]
            
        
        if rut_limpio_nuevo == rut_limpio_antiguo and not pass_es_nueva:
            raise ValueError("No hay cambios que guardar.")

        # Si el RUT cambia, se borra la entrada antigua
        if rut_limpio_nuevo != rut_limpio_antiguo:
            del self.usuarios[rut_limpio_antiguo]
            self.usuarios[rut_limpio_nuevo] = {
                "id": user_id, 
                "password_hash": password_hash_nueva, 
                "salt": salt_nuevo
            }
        else:
            # Si solo cambia la contraseña
            self.usuarios[rut_limpio_nuevo]["password_hash"] = password_hash_nueva
            self.usuarios[rut_limpio_nuevo]["salt"] = salt_nuevo
            
        self._guardar_usuarios()


    def eliminar_usuario_y_datos(self, user_id: int, rut: str):
        rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()
        
        # Eliminar datos (cursos/alumnos/sesiones)
        if user_id in self.datos_por_usuario:
            del self.datos_por_usuario[user_id]
        
        # Eliminar usuario (login)
        if rut_limpio in self.usuarios:
            del self.usuarios[rut_limpio]
        
        self.guardar_todo()

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
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), sin espacios, y no debe ser un RUT repetitivo (ej: 11.111.111-1).") 
            
        rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()

        if rut_limpio in estudiantes:
            raise ValueError("RUT ya existe para este usuario.")
            
        # Validación: Verificar que el RUT no esté registrado como usuario (login)
        if rut_limpio in self.usuarios:
            raise ValueError("Este RUT ya está registrado para iniciar sesión y no puede ser usado como alumno.")
            
        # Validar nombre/apellido único (simplificado: ignorando espacios/mayúsculas/minúsculas)
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
        cursos = datos["cursos"]
        
        # Validaciones
        if not nuevo_nombre or not nuevo_rut:
             raise ValueError("Nombre y nuevo RUT son obligatorios.")
             
        if not validar_rut(nuevo_rut):
            raise ValueError("RUT inválido. Debe tener 7 u 8 dígitos, un verificador (0-9 o K), sin espacios, y no debe ser un RUT repetitivo (ej: 11.111.111-1).") 
            
        nuevo_rut_limpio = re.sub(r'[^0-9kK]', '', nuevo_rut).upper()
             
        st = estudiantes.get(rut_antiguo)
        if not st:
            raise ValueError("Alumno no encontrado.")
        
        if nuevo_rut_limpio != rut_antiguo and nuevo_rut_limpio in estudiantes:
            raise ValueError("Nuevo RUT ya existe para este usuario.")
            
        # Validación: Verificar que el nuevo RUT no esté registrado como usuario (login)
        if nuevo_rut_limpio != rut_antiguo and nuevo_rut_limpio in self.usuarios:
            raise ValueError("Nuevo RUT ya está registrado para iniciar sesión y no puede ser usado como alumno.")
        
        if nuevo_nombre.lower().strip() != st.nombre.lower().strip() and nuevo_nombre.lower().strip() in [s.nombre.lower().strip() for s in estudiantes.values() if s.rut != rut_antiguo]:
            raise ValueError("Ya existe otro estudiante con ese nombre y apellido.")

        # Si el RUT cambia, se elimina la entrada antigua y se crea la nueva
        if nuevo_rut_limpio != rut_antiguo:
            del estudiantes[rut_antiguo]
            # Actualiza sesiones
            for sess in sesiones.values():
                if rut_antiguo in sess.ruts_presentes:
                    sess.ruts_presentes.remove(rut_antiguo)
                    sess.ruts_presentes.add(nuevo_rut_limpio)
                if rut_antiguo in sess.ruts_justificados:
                    sess.ruts_justificados.remove(rut_antiguo)
                    sess.ruts_justificados.add(nuevo_rut_limpio)
            # Actualiza cursos (lista de estudiantes)
            for curso in cursos.values():
                if rut_antiguo in curso.estudiantes_ruts:
                    curso.estudiantes_ruts.remove(rut_antiguo)
                    curso.estudiantes_ruts.add(nuevo_rut_limpio)
        
        st.nombre = nuevo_nombre
        st.rut = nuevo_rut_limpio
        estudiantes[nuevo_rut_limpio] = st
        self._guardar_datos()
        return st

    def eliminar_estudiante(self, user_id: int, rut: str):
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        sesiones = datos["sesiones"]
        cursos = datos["cursos"]
        
        if rut not in estudiantes:
            raise ValueError("Alumno no encontrado.")

        del estudiantes[rut]
        
        # Eliminar de sesiones
        for sess in sesiones.values():
            if rut in sess.ruts_presentes:
                sess.ruts_presentes.remove(rut)
            if rut in sess.ruts_justificados:
                sess.ruts_justificados.remove(rut)
                
        # Eliminar de cursos
        for curso in cursos.values():
            if rut in curso.estudiantes_ruts:
                curso.estudiantes_ruts.remove(rut)
                
        self._guardar_datos()
    
    # --- Métodos de Curso (necesitan user_id) ---
    
    # **MODIFICADO** para manejar secciones y estudiantes iniciales
    def crear_curso(self, user_id: int, codigo_base: str, nombre_base: str, horario: str = "", num_secciones: int = 1, estudiantes_por_seccion: Optional[Dict[str, Set[str]]] = None) -> List[Curso]:
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]

        if not codigo_base or not nombre_base:
             raise ValueError("Código y nombre son obligatorios.")

        # Validación: Códigos de curso no repetidos entre usuarios (parte del requerimiento)
        for other_user_id, other_data in self.datos_por_usuario.items():
            if other_user_id != user_id:
                for codigo_existente in other_data["cursos"].keys():
                    if codigo_base == codigo_existente or codigo_base.split('-')[0] == codigo_existente.split('-')[0]:
                        raise ValueError("Existe un curso con este código base en otro usuario.")


        nuevos_cursos = []
        
        # Validación: Un estudiante no puede estar en dos secciones del mismo curso_base
        ruts_totales = set()
        if estudiantes_por_seccion:
            for ruts in estudiantes_por_seccion.values():
                ruts_totales.update(ruts)
                
        if len(ruts_totales) != sum(len(r) for r in estudiantes_por_seccion.values()):
            # Esto comprueba si hay un RUT en más de una de las listas de secciones
            raise ValueError("Un estudiante no puede estar asignado a dos secciones del mismo curso base.")
            
        for i in range(1, num_secciones + 1):
            codigo = f"{codigo_base}-{i}" if num_secciones > 1 else codigo_base
            nombre = f"{nombre_base} - Sección {i}" if num_secciones > 1 else nombre_base
            
            if codigo in cursos:
                raise ValueError(f"Código de curso '{codigo}' ya existe.")
                
            # Validación de nombre (solo se comprueba el nombre base para evitar repeticiones de nombres de curso base)
            nombre_check = nombre_base.lower().strip()
            if num_secciones == 1 and nombre_check in [c.nombre.lower().strip() for c in cursos.values()]:
                 raise ValueError("Ya existe un curso con este nombre.")
            elif num_secciones > 1 and nombre_check in [c.nombre.split(' - ')[0].lower().strip() for c in cursos.values() if ' - Sección ' in c.nombre]:
                raise ValueError("Ya existe un curso base con este nombre.")
            

            ruts_seccion = estudiantes_por_seccion.get(str(i), set()) if estudiantes_por_seccion else set()
            co = Curso(codigo, nombre, horario, list(ruts_seccion))
            cursos[codigo] = co
            nuevos_cursos.append(co)
            
        self._guardar_datos()
        return nuevos_cursos

    def actualizar_curso(self, user_id: int, codigo_antiguo: str, codigo_nuevo: str, nombre: str, horario: str) -> Curso:
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        sesiones = datos["sesiones"]
        
        if not codigo_nuevo or not nombre:
             raise ValueError("Código y nombre son obligatorios.")

        if codigo_antiguo not in cursos:
            raise ValueError("Curso no encontrado.")
            
        curso_actual = cursos.get(codigo_antiguo)
        if curso_actual.cerrado: # **NUEVA FUNCIONALIDAD**
            raise ValueError("Este curso ya fue cerrado y no se puede editar.")
            
        if codigo_nuevo != codigo_antiguo and codigo_nuevo in cursos:
            raise ValueError("Nuevo código ya existe.")
            
        # Validación de nombre (ignorar si el nombre no cambia o es una sección)
        is_section = ' - Sección ' in curso_actual.nombre
        nombre_comparacion = nombre.lower().strip()
        
        if is_section:
            # Si es una sección, solo se actualiza la parte de la sección
            if nombre_comparacion != curso_actual.nombre.lower().strip():
                raise ValueError("No se permite cambiar el nombre del curso base de una sección directamente.")
        else:
            # Si no es sección, validar que no se repita con otros cursos no-sección
            if nombre_comparacion != curso_actual.nombre.lower().strip() and nombre_comparacion in [c.nombre.lower().strip() for c in cursos.values() if c.codigo != codigo_antiguo and ' - Sección ' not in c.nombre]:
                raise ValueError("Ya existe un curso con este nombre.")

        co = cursos.pop(codigo_antiguo)
        co.codigo = codigo_nuevo
        co.nombre = nombre
        co.horario = horario
        cursos[codigo_nuevo] = co
        
        # Actualizar código en las sesiones
        for s in sesiones.values():
            if s.codigo_curso == codigo_antiguo:
                s.codigo_curso = codigo_nuevo
                
        self._guardar_datos()
        return co
        
    def asignar_estudiantes_a_curso(self, user_id: int, codigo_curso: str, ruts_a_asignar: Set[str]):
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        
        if codigo_curso not in cursos:
            raise ValueError("Curso no encontrado.")
            
        curso_actual = cursos[codigo_curso]
        if curso_actual.cerrado: # **NUEVA FUNCIONALIDAD**
            raise ValueError("Este curso ya fue cerrado y no se puede editar a los estudiantes.")
        
        # Validar si algún RUT a asignar está en otra sección del mismo curso base
        curso_base_codigo = codigo_curso.split('-')[0]
        curso_actual_seccion = codigo_curso.split('-')[1] if len(codigo_curso.split('-')) > 1 else None

        for codigo, curso in cursos.items():
            if curso.codigo != codigo_curso and curso.codigo.split('-')[0] == curso_base_codigo:
                # Es otra sección del mismo curso base
                ruts_en_otra_seccion = curso.estudiantes_ruts.intersection(ruts_a_asignar)
                if ruts_en_otra_seccion:
                    raise ValueError(f"El estudiante con RUT {list(ruts_en_otra_seccion)[0]} ya está en la sección {codigo}.")
        
        curso_actual.estudiantes_ruts = ruts_a_asignar
        self._guardar_datos()
        
    def cerrar_curso(self, user_id: int, codigo_curso: str):
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        
        if codigo_curso not in cursos:
            raise ValueError("Curso no encontrado.")
            
        curso = cursos[codigo_curso]
        if curso.cerrado:
            raise ValueError("Este curso ya fue cerrado.")
            
        curso.cerrado = True
        curso.nombre += " (CERRADO)"
        self._guardar_datos()
        
    def definir_min_asistencia(self, user_id: int, codigo_curso: str, min_asistencia: float):
        datos = self._obtener_datos_usuario(user_id)
        cursos = datos["cursos"]
        
        if codigo_curso not in cursos:
            raise ValueError("Curso no encontrado.")
        if not (60.0 <= min_asistencia <= 100.0):
            raise ValueError("El mínimo de asistencia debe estar entre 60% y 100%.")
            
        cursos[codigo_curso].min_asistencia = min_asistencia
        self._guardar_datos()

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
            
        if cursos[codigo_curso].cerrado: # **NUEVA FUNCIONALIDAD**
            raise ValueError("Este curso ya fue cerrado y no se pueden crear sesiones.")
            
        sess = Sesion(siguiente_id_sesion, codigo_curso, datetime.now(), []) 
        sesiones[sess.id] = sess
        datos["siguiente_id_sesion"] += 1
        self._guardar_datos()
        return sess

    # **MODIFICADO** para incluir justificados
    def editar_sesion(self, user_id: int, sesion_id: int, nueva_fecha: Optional[datetime] = None, nuevos_ruts_presentes: Optional[Set[str]] = None, nuevos_ruts_justificados: Optional[Set[str]] = None):
        datos = self._obtener_datos_usuario(user_id)
        estudiantes = datos["estudiantes"]
        sesiones = datos["sesiones"]
        cursos = datos["cursos"]
        
        sess = sesiones.get(sesion_id)
        if not sess:
            raise ValueError("Sesión no encontrada.")
            
        if cursos[sess.codigo_curso].cerrado: # **NUEVA FUNCIONALIDAD**
            raise ValueError("Este curso ya fue cerrado y no se pueden modificar sesiones.")
        
        ruts_validos_globales = set(estudiantes.keys())
        ruts_curso = cursos[sess.codigo_curso].estudiantes_ruts # Solo Ruts asignados al curso
            
        if nueva_fecha:
            sess.fecha = nueva_fecha
            
        if nuevos_ruts_presentes is not None:
            # Solo permitir presentes si son estudiantes válidos Y están asignados al curso
            sess.ruts_presentes = ruts_curso.intersection(ruts_validos_globales).intersection(nuevos_ruts_presentes)
            
        if nuevos_ruts_justificados is not None:
            # Solo permitir justificados si son estudiantes válidos Y están asignados al curso
            sess.ruts_justificados = ruts_curso.intersection(ruts_validos_globales).intersection(nuevos_ruts_justificados)
            
        self._guardar_datos()

    def eliminar_sesion(self, user_id: int, sesion_id: int):
        datos = self._obtener_datos_usuario(user_id)
        sesiones = datos["sesiones"]
        cursos = datos["cursos"]
        
        if sesion_id not in sesiones:
            raise ValueError("Sesión no encontrada.")
            
        sess = sesiones[sesion_id]
        if cursos[sess.codigo_curso].cerrado: # **NUEVA FUNCIONALIDAD**
            raise ValueError("Este curso ya fue cerrado y no se pueden eliminar sesiones.")
            
        del sesiones[sesion_id]
        self._guardar_datos()

    def obtener_sesiones_por_curso(self, user_id: int, codigo_curso: str) -> List[Sesion]:
        datos = self._obtener_datos_usuario(user_id)
        return [s for s in datos["sesiones"].values() if s.codigo_curso == codigo_curso]


    def porcentaje_asistencia_por_estudiante(self, user_id: int, codigo_curso: str, rut_estudiante: str) -> float:
        datos = self._obtener_datos_usuario(user_id)
        curso = datos["cursos"].get(codigo_curso)
        
        if not curso or rut_estudiante not in curso.estudiantes_ruts:
             # Si el curso no existe o el estudiante no está en el curso, el cálculo es 0.0
            return 0.0

        sesiones_usuario = self.obtener_sesiones_por_curso(user_id, codigo_curso)
        
        # Filtrar sesiones solo donde el estudiante está asignado.
        sesiones_relevantes = [s for s in sesiones_usuario if rut_estudiante in curso.estudiantes_ruts]
        
        if not sesiones_relevantes:
            return 100.0 if rut_estudiante in curso.estudiantes_ruts else 0.0
            
        # Un estudiante asiste si está en ruts_presentes O si está en ruts_justificados (requerimiento 6)
        asistido = sum(1 for s in sesiones_relevantes if rut_estudiante in s.ruts_presentes or rut_estudiante in s.ruts_justificados)
        
        return (asistido / len(sesiones_relevantes)) * 100.0


# --- GUI (Interfaz del customtkinter) ---
class AppGUI(ctk.CTk):
    def __init__(self, sistema: SistemaAsistencia):
        super().__init__()
        self.sistema = sistema
        ctk.set_appearance_mode("White")
        ctk.set_default_color_theme("blue")
        self.title("Sistema de Asistencia para Profesores")
        ctk.set_widget_scaling(1.1)
        self.geometry("1280x720")

        self.usuario_logueado: Optional[str] = None # RUT del usuario logueado
        self.user_id: Optional[int] = None # ID interno
        
        # Variables de estado para edición
        self.rut_seleccionado_actual: Optional[str] = None
        self.codigo_seleccionado_actual: Optional[str] = None
        self.curso_base_secciones: Optional[str] = None # Para la creación de cursos con secciones

        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=10, pady=8)
        self.etiqueta_titulo = ctk.CTkLabel(header, text="Sistema de Asistencia para Profesores", font=("Arial", 24, "bold"))
        self.etiqueta_titulo.pack(side="left", padx=10)
        self.etiqueta_usuario = ctk.CTkLabel(header, text="Sin sesión", font=("Arial", 24))
        self.etiqueta_usuario.pack(side="right", padx=10)
        self.boton_logout = ctk.CTkButton(header, text="Cerrar sesion", command=self.logout, state="disabled", font=("Arial", 24))
        self.boton_logout.pack(side="right", padx=10)
        
        # **NUEVA FUNCIONALIDAD** - Botón de configuración
        self.boton_config = ctk.CTkButton(header, text="Configurar Usuario", command=self.ui_configurar_usuario, state="disabled", font=("Arial", 24))
        self.boton_config.pack(side="right", padx=10)

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
        for b in (self.btn_vista_cursos, self.btn_vista_alumnos, self.btn_vista_sesiones, self.btn_vista_porcentajes, self.boton_logout, self.boton_config):
            b.configure(state=estado)
        
        if estado == "normal":
             self.btn_vista_login.configure(state="disabled") 
        else: 
             self.btn_vista_login.configure(state="normal") 

    def construir_frame_login(self):
        frm = ctk.CTkFrame(self.contenido)

        lbl = ctk.CTkLabel(frm, text="Iniciar sesión o registrarse", font=("Arial", 40, "bold"))
        lbl.pack(pady=20)
        
        # RUT
        ctk.CTkLabel(frm, text="RUT (ej: 21123456K, sin puntos, ni guion)", font=("Arial", 25)).pack(pady=4)
        self.entrada_rut_login = ctk.CTkEntry(frm, width=300) 
        self.entrada_rut_login.pack(pady=10)
        
        # Contraseña
        ctk.CTkLabel(frm, text="Contraseña (de 6 a 20 caracteres, sin espacios)", font=("Arial", 25)).pack(pady=4)
        self.entrada_pass_login = ctk.CTkEntry(frm, show="*", width=300)
        self.entrada_pass_login.pack(pady=10)

        btn_login = ctk.CTkButton(frm, text="Iniciar sesión", command=self.accion_login, font=("Arial", 27))
        btn_register = ctk.CTkButton(frm, text="Registrarse", command=self.accion_registrar, font=("Arial", 27))
        btn_login.pack(pady=10)
        btn_register.pack(pady=10)

        self.mensaje_login = ctk.CTkLabel(frm, text="") 
        self.mensaje_login.pack(pady=10)

        return frm

    def construir_frame_cursos(self):
        frm = ctk.CTkFrame(self.contenido)
        top = ctk.CTkFrame(frm)
        top.pack(side="top", fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Crear / Modificar Cursos", font=("Arial", 30, "bold")).pack(side="left", padx=10)

        campos = ctk.CTkFrame(frm)
        campos.pack(side="top", fill="x", padx=10, pady=10)
        
        input_frame = ctk.CTkFrame(campos)
        input_frame.pack(pady=5)
        
        ctk.CTkLabel(input_frame, text="Código Base (ej: CS101):", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_codigo_curso = ctk.CTkEntry(input_frame)
        self.entrada_codigo_curso.pack(side="left", padx=10)
        
        ctk.CTkLabel(input_frame, text="Nombre Base:", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_nombre_curso = ctk.CTkEntry(input_frame)
        self.entrada_nombre_curso.pack(side="left", padx=10)
        
        ctk.CTkLabel(input_frame, text="Horario:", font=("Arial",20)).pack(side="left", padx=10)
        self.entrada_horario_curso = ctk.CTkEntry(input_frame)
        self.entrada_horario_curso.pack(side="left", padx=10)
        
        # **NUEVA FUNCIONALIDAD** - Seleccionar Secciones (solo para crear)
        ctk.CTkLabel(input_frame, text="Secciones (1-3):", font=("Arial",20)).pack(side="left", padx=10)
        self.combo_secciones = ctk.CTkComboBox(input_frame, values=["1", "2", "3"], font=("Arial", 20), width=60)
        self.combo_secciones.set("1")
        self.combo_secciones.pack(side="left", padx=10)


        btns = ctk.CTkFrame(campos)
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Crear Curso/Secciones", command=self.ui_preparar_crear_curso, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Editar seleccionado", command=self.ui_editar_curso, font=("Arial", 22)).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Borrar seleccionado", command=self.ui_eliminar_curso, font=("Arial", 22)).pack(side="left", padx=10)
        # **NUEVA FUNCIONALIDAD** - Botón para editar alumnos
        ctk.CTkButton(btns, text="Editar Alumnos", command=self.ui_preparar_editar_alumnos_curso, font=("Arial", 22), fg_color="green").pack(side="left", padx=10)
        # **NUEVA FUNCIONALIDAD** - Botón para cerrar curso
        ctk.CTkButton(btns, text="Cerrar Curso", command=self.ui_cerrar_curso, font=("Arial", 22), fg_color="red").pack(side="left", padx=10)
        

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf, text="Lista de Cursos:", font=("Arial", 30, "bold")).pack(anchor="w", padx=10)
        
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
        
        # **NUEVA FUNCIONALIDAD** - Búsqueda de alumnos y cursos
        busqueda_frame = ctk.CTkFrame(campos)
        busqueda_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(busqueda_frame, text="Buscar por Nombre:", font=("Arial", 20)).pack(side="left", padx=10)
        self.entrada_busqueda_alumno = ctk.CTkEntry(busqueda_frame, width=250)
        self.entrada_busqueda_alumno.pack(side="left", padx=10)
        ctk.CTkButton(busqueda_frame, text="Buscar", command=self.ui_buscar_alumnos, font=("Arial", 22)).pack(side="left", padx=10)


        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        
        listf_left = ctk.CTkFrame(listf)
        listf_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf_left, text="Lista de Alumnos:", font=("Arial", 30, "bold")).pack(anchor="w", padx=10)
        self.listbox_alumnos = tk.Listbox(listf_left, height=24, font=("Arial", 24), exportselection=False)
        self.listbox_alumnos.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        sb_al = tk.Scrollbar(listf_left, command=self.listbox_alumnos.yview)
        sb_al.pack(side="right", fill="y")
        self.listbox_alumnos.config(yscrollcommand=sb_al.set)
        self.listbox_alumnos.bind("<<ListboxSelect>>", self.llenar_formulario_alumno) 
        
        listf_right = ctk.CTkFrame(listf)
        listf_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(listf_right, text="Cursos del Alumno Seleccionado:", font=("Arial", 25, "bold")).pack(anchor="w", padx=10)
        self.listbox_cursos_alumno = tk.Listbox(listf_right, height=24, font=("Arial", 24))
        self.listbox_cursos_alumno.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        sb_co = tk.Scrollbar(listf_right, command=self.listbox_cursos_alumno.yview)
        sb_co.pack(side="right", fill="y")
        self.listbox_cursos_alumno.config(yscrollcommand=sb_co.set)


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
        ctk.CTkLabel(leftf, text="Lista de Alumnos del Curso (Referencia)", font=("Arial", 22, "bold")).pack(anchor="w", padx=10)
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

        mid = ctk.CTkFrame(frm)
        mid.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(mid, text="Seleccionar Curso:", font=("Arial", 25, "bold")).pack(side="left", padx=10)
        self.combo_curso_porcentajes = ctk.CTkComboBox(mid, values=[], font=("Arial", 22))
        self.combo_curso_porcentajes.pack(side="left", padx=10)
        self.combo_curso_porcentajes.configure(command=self.refrescar_lista_porcentajes)
        
        # **NUEVA FUNCIONALIDAD** - Mínimo de asistencia
        ctk.CTkLabel(mid, text="Mínimo de Asistencia (60-100%):", font=("Arial", 25, "bold")).pack(side="left", padx=20)
        self.entrada_min_asistencia = ctk.CTkEntry(mid, width=70, font=("Arial", 22))
        self.entrada_min_asistencia.pack(side="left", padx=10)
        ctk.CTkButton(mid, text="Definir Mínimo", command=self.ui_definir_minimo_asistencia, font=("Arial", 22)).pack(side="left", padx=10)

        listf = ctk.CTkFrame(frm)
        listf.pack(fill="both", expand=True, padx=10, pady=10)
        
        leftf = ctk.CTkFrame(listf)
        leftf.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(leftf, text="Asistencia por Alumno:", font=("Arial", 25, "bold")).pack(anchor="w", padx=10)
        self.listbox_porcentajes = tk.Listbox(leftf, font=("Arial", 22))
        self.listbox_porcentajes.pack(fill="both", expand=True, padx=10, pady=10)
        self.listbox_porcentajes.bind("<<ListboxSelect>>", self.ui_mostrar_historial_asistencia) # **NUEVA FUNCIONALIDAD**

        rightf = ctk.CTkFrame(listf)
        rightf.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(rightf, text="Historial de Asistencia / Inasistencia:", font=("Arial", 25, "bold")).pack(anchor="w", padx=10)
        self.listbox_historial = tk.Listbox(rightf, font=("Arial", 20))
        self.listbox_historial.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(rightf, text="Justificar Inasistencia (Sesión seleccionada)", command=self.ui_justificar_inasistencia, font=("Arial", 20), fg_color="blue").pack(pady=5)
        ctk.CTkButton(rightf, text="Quitar Justificación (Sesión seleccionada)", command=self.ui_quitar_justificacion, font=("Arial", 20), fg_color="orange").pack(pady=5)
        

        return frm
    
    # Mostrar frames
    def limpiar_contenido(self):
        for w in self.contenido.winfo_children():
            w.pack_forget()

    def mostrar_login_frame(self):
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
        self.codigo_seleccionado_actual = None 
        self.curso_base_secciones = None

    def mostrar_alumnos(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_alumnos:
            self.frame_alumnos = self.construir_frame_alumnos()
        self.frame_alumnos.pack(fill="both", expand=True)
        self.refrescar_lista_alumnos()
        self.rut_seleccionado_actual = None
        self.listbox_cursos_alumno.delete(0, "end") # Limpiar lista de cursos al cambiar de vista

    def mostrar_sesiones(self):
        if not self.verificar_logueo(): return
        self.limpiar_contenido()
        if not self.frame_sesiones:
            self.frame_sesiones = self.construir_frame_sesiones()
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        cursos_keys = sorted(list(datos_usuario.get("cursos", {}).keys()))
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
        cursos_keys = sorted(list(datos_usuario.get("cursos", {}).keys()))
        self.combo_curso_porcentajes.configure(values=cursos_keys)
        
        self.listbox_historial.delete(0, "end") # Limpiar historial

        if cursos_keys:
            # Obtener el primer curso
            codigo_curso = cursos_keys[0]
            self.combo_curso_porcentajes.set(codigo_curso)
            # Mostrar min asistencia y refrescar
            self.entrada_min_asistencia.delete(0, "end")
            self.entrada_min_asistencia.insert(0, str(datos_usuario["cursos"].get(codigo_curso).min_asistencia))
            self.refrescar_lista_porcentajes(codigo_curso)
        else:
            self.combo_curso_porcentajes.set("")
            self.listbox_porcentajes.delete(0, "end")
            self.entrada_min_asistencia.delete(0, "end")
            
        self.frame_porcentajes.pack(fill="both", expand=True)

    # Login/Registro
    def accion_registrar(self):
        rut = self.entrada_rut_login.get().strip() 
        p = self.entrada_pass_login.get().strip()
        try:
            self.sistema.registrar_usuario(rut, p) 
            messagebox.showinfo("Registro Exitoso", "Usuario creado. Inicia sesión.")
            self.mensaje_login.configure(text="Usuario creado. Inicia sesión.", text_color="green")
            self.entrada_rut_login.delete(0, "end")
            self.entrada_pass_login.delete(0, "end")
        except ValueError as e:
            messagebox.showerror("Error de Registro", str(e))
            self.mensaje_login.configure(text="") # Limpiar mensaje de éxito previo

    def accion_login(self):
        rut = self.entrada_rut_login.get().strip() 
        p = self.entrada_pass_login.get().strip()
        
        if ' ' in rut:
            messagebox.showerror("Error de Autenticación", "El RUT no debe contener espacios.")
            self.mensaje_login.configure(text="")
            return

        if not validar_rut(rut):
            # Usar una validación menos estricta para el login, ya que podría estar registrado un RUT "repetitivo" de antes.
            # Solo se verifica formato general.
            rut_limpio = re.sub(r'[^0-9kK]', '', rut).upper()
            if not re.match(r'^\d{7,8}[0-9K]$', rut_limpio):
                messagebox.showerror("Error de Autenticación", "Formato de RUT incorrecto.")
                self.mensaje_login.configure(text="")
                return

        user_id = self.sistema.verificar_usuario(rut, p) 
        
        if user_id is not None:
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
            self.mensaje_login.configure(text="")

    def logout(self):
        self.usuario_logueado = None
        self.user_id = None
        messagebox.showinfo("Logout", "Sesión cerrada.")
        self.etiqueta_usuario.configure(text="Sin sesión")
        self.actualizar_botones_nav("disabled") 
        self.mostrar_login_frame() 
        
    # **NUEVA FUNCIONALIDAD** - Configurar Usuario
    def ui_configurar_usuario(self):
        if not self.verificar_logueo(): return
        
        top = tk.Toplevel(self)
        top.title("Configuración de Usuario")
        top.geometry("600x600")
        
        rut_usuario = self.usuario_logueado 
        
        ctk.CTkLabel(top, text=f"Configurar Cuenta: {rut_usuario}", font=("Arial", 30, "bold")).pack(pady=20)
        
        ctk.CTkLabel(top, text="RUT Antiguo/Actual:", font=("Arial", 20)).pack(pady=5)
        entrada_rut_antiguo = ctk.CTkEntry(top, width=300, state="disabled")
        entrada_rut_antiguo.insert(0, rut_usuario)
        entrada_rut_antiguo.pack(pady=5)
        
        ctk.CTkLabel(top, text="Contraseña Actual para Confirmar:", font=("Arial", 20)).pack(pady=5)
        entrada_pass_confirmacion = ctk.CTkEntry(top, width=300, show="*")
        entrada_pass_confirmacion.pack(pady=5)
        
        ctk.CTkLabel(top, text="Nuevo RUT (dejar vacío si no cambia):", font=("Arial", 20)).pack(pady=5)
        entrada_nuevo_rut = ctk.CTkEntry(top, width=300)
        entrada_nuevo_rut.insert(0, rut_usuario) # Por defecto es el mismo
        entrada_nuevo_rut.pack(pady=5)
        
        ctk.CTkLabel(top, text="Nueva Contraseña (dejar vacío si no cambia):", font=("Arial", 20)).pack(pady=5)
        entrada_nueva_pass = ctk.CTkEntry(top, width=300, show="*")
        entrada_nueva_pass.pack(pady=5)
        
        def guardar_cambios():
            pass_confirm = entrada_pass_confirmacion.get().strip()
            nuevo_rut = entrada_nuevo_rut.get().strip()
            nueva_pass = entrada_nueva_pass.get().strip()
            
            # 1. Verificar contraseña actual
            if not pass_confirm:
                messagebox.showerror("Error", "Debe ingresar la contraseña actual para confirmar los cambios.")
                return
                
            user_id_check = self.sistema.verificar_usuario(rut_usuario, pass_confirm)
            if user_id_check is None:
                messagebox.showerror("Error", "Contraseña actual incorrecta.")
                return

            try:
                # 2. Asignar valores por defecto si están vacíos
                final_rut = nuevo_rut if nuevo_rut else rut_usuario
                final_pass = nueva_pass if nueva_pass else pass_confirm

                self.sistema.actualizar_usuario(
                    self.user_id, 
                    rut_usuario, # Antiguo RUT (logueado)
                    final_rut, 
                    final_pass
                )
                
                # 3. Actualizar el estado de la GUI si el RUT cambió
                if final_rut != rut_usuario:
                    self.usuario_logueado = final_rut # Se actualiza el RUT logueado
                    self.etiqueta_usuario.configure(text=f"RUT: {self.usuario_logueado}")
                    
                messagebox.showinfo("Éxito", "Cuenta de usuario actualizada. Deberás volver a iniciar sesión si cambiaste la contraseña.")
                top.destroy()
                # Si se cambió el RUT o la contraseña, forzar logout (por simplicidad, si cambia la contraseña, forzamos login de nuevo)
                if final_rut != rut_usuario or nueva_pass:
                    self.logout()
                    
            except ValueError as e:
                messagebox.showerror("Error al guardar", str(e))

        def eliminar_cuenta():
            pass_confirm = entrada_pass_confirmacion.get().strip()
            
            # 1. Verificar contraseña actual
            if not pass_confirm:
                messagebox.showerror("Error", "Debe ingresar la contraseña actual para confirmar la eliminación.")
                return
                
            user_id_check = self.sistema.verificar_usuario(rut_usuario, pass_confirm)
            if user_id_check is None:
                messagebox.showerror("Error", "Contraseña actual incorrecta.")
                return

            if messagebox.askyesno("Confirmar Eliminación", "⚠️ ¿Seguro que quieres BORRAR este usuario? Se borrará **todo el registro de estudiantes y clases** asociado a esta cuenta."):
                try:
                    self.sistema.eliminar_usuario_y_datos(self.user_id, rut_usuario)
                    messagebox.showinfo("Éxito", "Cuenta y datos eliminados correctamente.")
                    top.destroy()
                    self.logout() # Logout automático
                except Exception as e:
                    messagebox.showerror("Error al eliminar", f"Ocurrió un error: {str(e)}")


        ctk.CTkButton(top, text="Guardar Cambios", command=guardar_cambios, font=("Arial", 22)).pack(pady=10)
        ctk.CTkButton(top, text="Eliminar Cuenta (Requiere Contraseña)", command=eliminar_cuenta, font=("Arial", 22), fg_color="red").pack(pady=10)


    # Cursos
    def refrescar_lista_cursos(self):
        if not self.verificar_logueo(): return
        self.listbox_cursos.delete(0, "end")
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        for codigo, c in sorted(datos_usuario.get("cursos", {}).items()):
            # Mostrar el mínimo de asistencia si es un curso no cerrado
            min_asist = f" | Mín. Asist.: {c.min_asistencia:.1f}%" if not c.cerrado else ""
            self.listbox_cursos.insert("end", f"{codigo} - {c.nombre} ({c.horario}){min_asist}")
        self.codigo_seleccionado_actual = None 

    def llenar_formulario_curso(self, event=None):
        sel = self.listbox_cursos.curselection()
        if not sel or not self.verificar_logueo():
            self.codigo_seleccionado_actual = None 
            return
        
        txt = self.listbox_cursos.get(sel[0])
        codigo = txt.split(" - ")[0]
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        c = datos_usuario.get("cursos", {}).get(codigo)
        
        if not c:
            self.codigo_seleccionado_actual = None
            return
        
        self.codigo_seleccionado_actual = c.codigo
        
        # Limpiar/insertar en los campos (cuidado con secciones para el código/nombre)
        codigo_mostrar = c.codigo.split('-')[0] if ' - Sección ' in c.nombre else c.codigo
        nombre_mostrar = c.nombre.split(' - Sección ')[0] if ' - Sección ' in c.nombre else c.nombre
        
        self.entrada_codigo_curso.delete(0, "end")
        self.entrada_nombre_curso.delete(0, "end")
        self.entrada_horario_curso.delete(0, "end")
        self.entrada_codigo_curso.insert(0, codigo_mostrar)
        self.entrada_nombre_curso.insert(0, nombre_mostrar)
        self.entrada_horario_curso.insert(0, c.horario)
        self.combo_secciones.set("1") # Resetear secciones, ya que solo aplica a la creación

    # **NUEVA FUNCIONALIDAD** - Lógica de creación con secciones y asignación de alumnos
    def ui_preparar_crear_curso(self):
        if not self.verificar_logueo(): return
        
        codigo = self.entrada_codigo_curso.get().strip()
        nombre = self.entrada_nombre_curso.get().strip()
        horario = self.entrada_horario_curso.get().strip()
        num_secciones = int(self.combo_secciones.get())
        
        if not codigo or not nombre:
             messagebox.showerror("Error", "Código y nombre son obligatorios.")
             return

        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        alumnos_disponibles = sorted([st for st in datos_usuario.get("estudiantes", {}).values()], key=lambda s: s.nombre)

        if not alumnos_disponibles:
             messagebox.showwarning("Advertencia", "No hay alumnos registrados. Crea el curso y añade alumnos después.")
             try:
                 self.sistema.crear_curso(self.user_id, codigo, nombre, horario, num_secciones)
                 messagebox.showinfo("Éxito", "Curso/s creado/s sin alumnos.")
                 self.refrescar_lista_cursos()
             except ValueError as e:
                 messagebox.showerror("Error", str(e))
             return
             
        self.curso_base_secciones = codigo # Guardar el código base para la lógica de asignación
        self.mostrar_ventana_asignacion_alumnos(codigo, nombre, num_secciones, 1, horario, {})


    def mostrar_ventana_asignacion_alumnos(self, codigo_base: str, nombre_base: str, total_secciones: int, seccion_actual: int, horario: str, ruts_por_seccion_acumulado: Dict[str, Set[str]]):
        
        top = tk.Toplevel(self)
        top.title(f"Asignar Estudiantes - {nombre_base} (Sección {seccion_actual}/{total_secciones})")
        top.geometry("700x700")
        
        # Obtener todos los alumnos disponibles
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        alumnos_disponibles = sorted([st for st in datos_usuario.get("estudiantes", {}).values()], key=lambda s: s.nombre)
        
        ruts_en_otras_secciones = set()
        for ruts in ruts_por_seccion_acumulado.values():
            ruts_en_otras_secciones.update(ruts)
            
        var_map = {}
        checkbox_frame = ctk.CTkFrame(top)
        checkbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(checkbox_frame, text=f"Selecciona los alumnos para la Sección {seccion_actual}:", font=("Arial", 20, "bold")).pack(pady=10)

        canvas = tk.Canvas(checkbox_frame)
        scrollbar = tk.Scrollbar(checkbox_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for st in alumnos_disponibles:
            estado_inicial = 0
            color = "white"
            state = "normal"
            if st.rut in ruts_en_otras_secciones:
                estado_inicial = 0
                color = "gray"
                state = "disabled" # No se puede seleccionar si ya está en otra sección
                
            var = tk.IntVar(value=estado_inicial)
            cb = ctk.CTkCheckBox(scrollable_frame, text=f"RUT: {st.rut} - {st.nombre} ({'EN OTRA SECCIÓN' if state=='disabled' else 'DISPONIBLE'})", 
                                 variable=var, font=("Arial", 18), state=state)
            cb.pack(anchor="w", padx=15, pady=2)
            var_map[st.rut] = var
            # Intentar cambiar el color del texto si está deshabilitado (no es trivial en CTk, se usa el texto de aviso)


        def siguiente_seccion():
            ruts_seleccionados = {rut for rut, var in var_map.items() if var.get() == 1}
            ruts_por_seccion_acumulado[str(seccion_actual)] = ruts_seleccionados
            top.destroy()
            
            if seccion_actual < total_secciones:
                # Pasar a la siguiente sección
                self.mostrar_ventana_asignacion_alumnos(codigo_base, nombre_base, total_secciones, seccion_actual + 1, horario, ruts_por_seccion_acumulado)
            else:
                # Finalizar y crear los cursos
                try:
                    self.sistema.crear_curso(self.user_id, codigo_base, nombre_base, horario, total_secciones, ruts_por_seccion_acumulado)
                    messagebox.showinfo("Éxito", f"Curso/s '{codigo_base}' y sus alumnos han sido creados correctamente.")
                    self.refrescar_lista_cursos()
                except ValueError as e:
                    messagebox.showerror("Error de Creación", str(e))
                finally:
                    self.curso_base_secciones = None
                    
        ctk.CTkButton(top, text="Siguiente Sección / Finalizar", command=siguiente_seccion, font=("Arial", 22)).pack(pady=10)
        ctk.CTkButton(top, text="Cancelar Creación", command=top.destroy, font=("Arial", 22)).pack(pady=5)
    
    
    # **NUEVA FUNCIONALIDAD** - Botón para editar alumnos de un curso
    def ui_preparar_editar_alumnos_curso(self):
        if not self.verificar_logueo(): return
        
        codigo_curso = self.codigo_seleccionado_actual
        if not codigo_curso:
            messagebox.showwarning("Seleccione", "Seleccione un curso de la lista para editar sus alumnos.")
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario.get("cursos", {}).get(codigo_curso)
        
        if not curso:
            messagebox.showerror("Error", "Curso no encontrado.")
            return

        if curso.cerrado:
            messagebox.showwarning("Curso Cerrado", "Este curso ya fue cerrado y no se pueden editar los estudiantes.")
            return
            
        self.mostrar_ventana_editar_alumnos_curso(curso)

    def mostrar_ventana_editar_alumnos_curso(self, curso: Curso):
        
        top = tk.Toplevel(self)
        top.title(f"Editar Estudiantes - {curso.nombre}")
        top.geometry("700x700")
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        alumnos_disponibles = sorted([st for st in datos_usuario.get("estudiantes", {}).values()], key=lambda s: s.nombre)
        
        ruts_en_otras_secciones = set()
        curso_base_codigo = curso.codigo.split('-')[0]
        
        # Encontrar alumnos en otras secciones del mismo curso base
        for codigo, c in datos_usuario["cursos"].items():
            if c.codigo != curso.codigo and c.codigo.split('-')[0] == curso_base_codigo:
                ruts_en_otras_secciones.update(c.estudiantes_ruts)
                
        var_map = {}
        checkbox_frame = ctk.CTkFrame(top)
        checkbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(checkbox_frame, text=f"Selecciona los alumnos para {curso.nombre}:", font=("Arial", 20, "bold")).pack(pady=10)

        canvas = tk.Canvas(checkbox_frame)
        scrollbar = tk.Scrollbar(checkbox_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for st in alumnos_disponibles:
            estado_inicial = 1 if st.rut in curso.estudiantes_ruts else 0
            state = "normal"
            etiqueta = f"RUT: {st.rut} - {st.nombre}"
            
            if st.rut in ruts_en_otras_secciones and st.rut not in curso.estudiantes_ruts:
                state = "disabled" # No se puede seleccionar si ya está en otra sección
                etiqueta += " (EN OTRA SECCIÓN)"
            elif st.rut in ruts_en_otras_secciones and st.rut in curso.estudiantes_ruts:
                # Esto no debería pasar si la lógica de las secciones funciona, pero se permite
                etiqueta += " (EN OTRA SECCIÓN - ¡ERROR DE DATOS!)"
            
            var = tk.IntVar(value=estado_inicial)
            cb = ctk.CTkCheckBox(scrollable_frame, text=etiqueta, 
                                 variable=var, font=("Arial", 18), state=state)
            cb.pack(anchor="w", padx=15, pady=2)
            var_map[st.rut] = var


        def aplicar_cambios():
            ruts_seleccionados = {rut for rut, var in var_map.items() if var.get() == 1}
            try:
                self.sistema.asignar_estudiantes_a_curso(self.user_id, curso.codigo, ruts_seleccionados)
                messagebox.showinfo("Éxito", f"Alumnos de '{curso.nombre}' actualizados correctamente.")
                top.destroy()
            except ValueError as e:
                messagebox.showerror("Error al guardar", str(e))
                
        ctk.CTkButton(top, text="Guardar Cambios", command=aplicar_cambios, font=("Arial", 22)).pack(pady=10)
        ctk.CTkButton(top, text="Cancelar", command=top.destroy, font=("Arial", 22)).pack(pady=5)


    def ui_crear_curso(self):
         # Redirigir a la función con lógica de secciones
         self.ui_preparar_crear_curso() 

    def ui_editar_curso(self):
        if not self.verificar_logueo(): return
        
        codigo_antiguo = self.codigo_seleccionado_actual
        if not codigo_antiguo:
            messagebox.showwarning("Seleccione", "Seleccione un curso para editar.")
            return
            
        codigo_nuevo = self.entrada_codigo_curso.get().strip()
        nuevo_nombre = self.entrada_nombre_curso.get().strip()
        nuevo_horario = self.entrada_horario_curso.get().strip()
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario["cursos"].get(codigo_antiguo)
        
        if curso.cerrado:
            messagebox.showwarning("Curso Cerrado", "Este curso ya fue cerrado y no se puede editar.")
            return

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
                
    def ui_cerrar_curso(self):
        if not self.verificar_logueo(): return
        codigo_curso = self.codigo_seleccionado_actual
        if not codigo_curso:
            messagebox.showwarning("Seleccione", "Seleccione un curso para cerrar.")
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario["cursos"].get(codigo_curso)
        
        if curso.cerrado:
            messagebox.showwarning("Curso Cerrado", "Este curso ya fue cerrado.")
            return

        if messagebox.askyesno("Confirmar Cierre", f"¿Seguro que quieres CERRAR el curso {codigo_curso} ('{curso.nombre}')? No se podrá editar ni registrar más sesiones."):
            try:
                self.sistema.cerrar_curso(self.user_id, codigo_curso)
                messagebox.showinfo("Éxito", f"Curso {codigo_curso} cerrado.")
                self.refrescar_lista_cursos()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    # Alumnos
    def refrescar_lista_alumnos(self):
        if not self.verificar_logueo(): return
        self.listbox_alumnos.delete(0, "end")
        self.listbox_cursos_alumno.delete(0, "end") # Limpiar lista de cursos
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items(), key=lambda x: x[1].nombre):
            self.listbox_alumnos.insert("end", f"RUT: {rut} - {st.nombre}") 
        self.rut_seleccionado_actual = None

    def llenar_formulario_alumno(self, event=None):
        sel = self.listbox_alumnos.curselection()
        self.listbox_cursos_alumno.delete(0, "end") # Limpiar lista de cursos
        
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
        
        self.rut_seleccionado_actual = st.rut
        
        self.entrada_nombre_alumno.delete(0, "end")
        self.entrada_rut_alumno.delete(0, "end")
        self.entrada_nombre_alumno.insert(0, st.nombre)
        self.entrada_rut_alumno.insert(0, st.rut)
        
        # **NUEVA FUNCIONALIDAD** - Mostrar cursos del alumno
        self.ui_mostrar_cursos_alumno(st.rut)

    def ui_mostrar_cursos_alumno(self, rut_estudiante: str):
        if not self.verificar_logueo(): return
        self.listbox_cursos_alumno.delete(0, "end")
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        cursos = datos_usuario.get("cursos", {})
        
        for codigo, curso in sorted(cursos.items()):
            if rut_estudiante in curso.estudiantes_ruts:
                
                if curso.cerrado:
                    # Determinar Aprobado/Reprobado
                    pct = self.sistema.porcentaje_asistencia_por_estudiante(self.user_id, codigo, rut_estudiante)
                    estado = "APROBADO" if pct >= curso.min_asistencia else "REPROBADO"
                    color = "green" if estado == "APROBADO" else "red"
                    
                    self.listbox_cursos_alumno.insert("end", f"{codigo} - {curso.nombre} | {estado} ({pct:.1f}%)")
                    # Intento de cambiar color (no es trivial en tk.Listbox, se usará el texto en mayúsculas)
                else:
                    # Mostrar porcentaje actual
                    pct = self.sistema.porcentaje_asistencia_por_estudiante(self.user_id, codigo, rut_estudiante)
                    self.listbox_cursos_alumno.insert("end", f"{codigo} - {curso.nombre} | Asistencia: {pct:.1f}%")
                    
    def ui_buscar_alumnos(self):
        if not self.verificar_logueo(): return
        nombre_busqueda = self.entrada_busqueda_alumno.get().strip().lower()
        
        self.listbox_alumnos.delete(0, "end")
        self.listbox_cursos_alumno.delete(0, "end")
        self.rut_seleccionado_actual = None
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        alumnos = datos_usuario.get("estudiantes", {})

        if not nombre_busqueda:
            self.refrescar_lista_alumnos()
            return
        
        resultados = []
        for rut, st in alumnos.items():
            if nombre_busqueda in st.nombre.lower():
                resultados.append(st)
                
        for st in sorted(resultados, key=lambda s: s.nombre):
             self.listbox_alumnos.insert("end", f"RUT: {st.rut} - {st.nombre}")
             
        if not resultados:
            messagebox.showinfo("Búsqueda", "No se encontraron alumnos con ese nombre.")

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
        
        rut_antiguo = self.rut_seleccionado_actual
        if not rut_antiguo:
            messagebox.showwarning("Seleccione", "Seleccione un alumno para editar.")
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
        if messagebox.askyesno("Confirmar", f"Eliminar alumno con RUT {rut}? Esto lo quita de todas las sesiones y cursos."):
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
        curso = datos_usuario.get("cursos", {}).get(codigo_curso)
        
        if not curso: return
            
        # alumnos solo del curso
        ruts_curso = curso.estudiantes_ruts
        
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items(), key=lambda x: x[1].nombre):
            if rut in ruts_curso:
                self.listbox_alumnos_sesiones.insert("end", f"RUT: {rut} - {st.nombre}")
            
        # sesiones:
        try:
            sesiones = self.sistema.obtener_sesiones_por_curso(self.user_id, codigo_curso)
            for s in sorted(sesiones, key=lambda x: x.fecha, reverse=True):
                # Calcular total de asistentes + justificados (como si fueran 'presentes efectivos')
                presentes_efectivos = len(s.ruts_presentes.union(s.ruts_justificados))
                self.listbox_sesiones.insert("end", f"{s.id} - {s.fecha.strftime('%Y-%m-%d %H:%M')} | Presentes Efectivos: {presentes_efectivos} (Justif.: {len(s.ruts_justificados)})") 
        except ValueError as e:
            messagebox.showerror("Error", str(e))


    def ui_iniciar_sesion(self):
        if not self.verificar_logueo(): return
        codigo_curso = self.combo_curso_sesiones.get()
        if not codigo_curso:
            messagebox.showwarning("Seleccione curso", "Seleccione un curso primero.")
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario["cursos"].get(codigo_curso)
        if curso.cerrado:
            messagebox.showwarning("Curso Cerrado", "Este curso ya fue cerrado.")
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
        curso = datos_usuario["cursos"].get(sess.codigo_curso)
        
        if not sess:
            messagebox.showerror("Error", "Sesión no encontrada.")
            return
            
        if curso.cerrado:
            messagebox.showwarning("Curso Cerrado", "Este curso ya fue cerrado.")
            return
            
        # Obtener solo alumnos asignados al curso
        ruts_curso = curso.estudiantes_ruts
        alumnos_sesion = sorted([st for st in datos_usuario["estudiantes"].values() if st.rut in ruts_curso], key=lambda s: s.nombre)

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
        
        presente_var_map = {}
        justificado_var_map = {}
        
        for st in alumnos_sesion: 
            # Inicializar con el estado actual
            esta_presente = 1 if st.rut in sess.ruts_presentes else 0
            esta_justificado = 1 if st.rut in sess.ruts_justificados else 0
            
            var_p = tk.IntVar(value=esta_presente)
            var_j = tk.IntVar(value=esta_justificado)
            
            frame_alumno = ctk.CTkFrame(scrollable_frame)
            frame_alumno.pack(fill="x", padx=15, pady=2)
            
            ctk.CTkLabel(frame_alumno, text=f"RUT: {st.rut} - {st.nombre}", font=("Arial", 22)).pack(side="left", padx=10)
            
            # Checkbox de Presente
            cb_p = ctk.CTkCheckBox(frame_alumno, text="Presente", variable=var_p, font=("Arial", 20)) 
            cb_p.pack(side="left", padx=20)
            
            # Checkbox de Justificado (Solo es relevante si NO está Presente)
            cb_j = ctk.CTkCheckBox(frame_alumno, text="Inasistencia Justificada", variable=var_j, font=("Arial", 20))
            cb_j.pack(side="left", padx=20)
            
            presente_var_map[st.rut] = var_p
            justificado_var_map[st.rut] = var_j

        def aplicar_cambios():
            nuevos_ruts_presentes = {rut for rut, var in presente_var_map.items() if var.get() == 1}
            nuevos_ruts_justificados = {rut for rut, var in justificado_var_map.items() if var.get() == 1}
            
            # Validación: No se puede estar Presente Y Justificado al mismo tiempo
            if nuevos_ruts_presentes.intersection(nuevos_ruts_justificados):
                messagebox.showerror("Error de Lógica", "Un alumno no puede estar marcado como 'Presente' y 'Justificado' en la misma sesión.")
                return

            try:
                self.sistema.editar_sesion(
                    self.user_id, 
                    sess_id, 
                    nuevos_ruts_presentes=nuevos_ruts_presentes,
                    nuevos_ruts_justificados=nuevos_ruts_justificados
                ) 
                messagebox.showinfo("Éxito", "Presentes y Justificados actualizados.")
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
        self.listbox_historial.delete(0, "end") # Limpiar historial
        
        codigo_curso = self.combo_curso_porcentajes.get()
        if not codigo_curso:
            return
            
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario.get("cursos", {}).get(codigo_curso)
        
        if not curso: return

        # Actualizar min asistencia
        self.entrada_min_asistencia.delete(0, "end")
        self.entrada_min_asistencia.insert(0, str(curso.min_asistencia))
        
        min_asistencia = curso.min_asistencia
        ruts_curso = curso.estudiantes_ruts
        
        for rut, st in sorted(datos_usuario.get("estudiantes", {}).items(), key=lambda x: x[1].nombre): 
            if rut in ruts_curso: # Solo alumnos de este curso
                pct = self.sistema.porcentaje_asistencia_por_estudiante(self.user_id, codigo_curso, rut) 
                tag = f"RUT: {rut} - {st.nombre} — {pct:.1f}%"
                
                self.listbox_porcentajes.insert("end", tag)
                
                # **NUEVA FUNCIONALIDAD** - Marcar en rojo si está por debajo del mínimo
                if pct < min_asistencia:
                    # Intento de color en rojo (Listbox de tk tiene tags para esto, pero CTk no las expone fácilmente, así que usamos un color de fondo para el item de tk.Listbox)
                    idx = self.listbox_porcentajes.size() - 1
                    self.listbox_porcentajes.itemconfig(idx, {'bg': 'red', 'fg': 'white'})


    def ui_definir_minimo_asistencia(self):
        if not self.verificar_logueo(): return
        codigo_curso = self.combo_curso_porcentajes.get()
        min_asistencia_str = self.entrada_min_asistencia.get().strip()
        
        if not codigo_curso:
            messagebox.showwarning("Seleccione curso", "Seleccione un curso primero.")
            return

        try:
            min_asistencia = float(min_asistencia_str)
            self.sistema.definir_min_asistencia(self.user_id, codigo_curso, min_asistencia)
            messagebox.showinfo("Éxito", "Mínimo de asistencia definido.")
            self.refrescar_lista_porcentajes(codigo_curso)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
             messagebox.showerror("Error", "Valor inválido o fuera del rango 60%-100%.")

    # **NUEVA FUNCIONALIDAD** - Historial de Asistencia
    def ui_mostrar_historial_asistencia(self, event=None):
        if not self.verificar_logueo(): return
        sel_p = self.listbox_porcentajes.curselection()
        
        self.listbox_historial.delete(0, "end")
        if not sel_p: return

        pct_txt = self.listbox_porcentajes.get(sel_p[0])
        rut_estudiante = pct_txt.split(" - ")[0].replace("RUT: ", "").strip() 
        codigo_curso = self.combo_curso_porcentajes.get()
        
        if not codigo_curso: return
        
        sesiones = self.sistema.obtener_sesiones_por_curso(self.user_id, codigo_curso)
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        curso = datos_usuario.get("cursos", {}).get(codigo_curso)
        
        if rut_estudiante not in curso.estudiantes_ruts: return # No mostrar historial si no pertenece al curso

        for s in sorted(sesiones, key=lambda x: x.fecha):
            estado = "NO APLICA"
            tag = {}
            if rut_estudiante in s.ruts_presentes:
                estado = "PRESENTE"
                tag = {'bg': 'green', 'fg': 'white'}
            elif rut_estudiante in s.ruts_justificados:
                estado = "JUSTIFICADA"
                tag = {'bg': 'blue', 'fg': 'white'}
            else:
                # Si está en el curso y no está en las listas, es inasistencia
                estado = "INASISTENTE"
                tag = {'bg': 'red', 'fg': 'white'}
                
            linea = f"ID {s.id} | {s.fecha.strftime('%Y-%m-%d %H:%M')} | {estado}"
            idx = self.listbox_historial.size()
            self.listbox_historial.insert("end", linea)
            self.listbox_historial.itemconfig(idx, tag)
            
    def _get_selected_historial(self):
        sel_h = self.listbox_historial.curselection()
        sel_p = self.listbox_porcentajes.curselection()
        if not sel_h or not sel_p:
            messagebox.showwarning("Selección Incompleta", "Seleccione un alumno y una sesión en el historial.")
            return None, None, None
            
        pct_txt = self.listbox_porcentajes.get(sel_p[0])
        rut_estudiante = pct_txt.split(" - ")[0].replace("RUT: ", "").strip() 
        codigo_curso = self.combo_curso_porcentajes.get()
        
        hist_txt = self.listbox_historial.get(sel_h[0])
        sess_id = int(hist_txt.split(" | ")[0].replace("ID ", ""))
        
        return sess_id, codigo_curso, rut_estudiante
            

    def ui_justificar_inasistencia(self):
        if not self.verificar_logueo(): return
        sess_id, codigo_curso, rut_estudiante = self._get_selected_historial()
        if not sess_id: return
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        sess = datos_usuario["sesiones"].get(sess_id)
        
        if rut_estudiante in sess.ruts_presentes:
            messagebox.showwarning("Ya Presente", "El alumno ya está marcado como presente. No se puede justificar.")
            return
            
        if rut_estudiante in sess.ruts_justificados:
            messagebox.showwarning("Ya Justificado", "El alumno ya está justificado en esta sesión.")
            return
        
        # Actualizar la sesión: quitar de presentes (si estuviera) y añadir a justificados
        nuevos_ruts_presentes = sess.ruts_presentes.copy()
        nuevos_ruts_justificados = sess.ruts_justificados.copy()
        
        if rut_estudiante in nuevos_ruts_presentes:
            nuevos_ruts_presentes.remove(rut_estudiante)
            
        nuevos_ruts_justificados.add(rut_estudiante)
        
        try:
            self.sistema.editar_sesion(self.user_id, sess_id, nuevos_ruts_presentes=nuevos_ruts_presentes, nuevos_ruts_justificados=nuevos_ruts_justificados)
            messagebox.showinfo("Éxito", "Inasistencia justificada.")
            self.refrescar_lista_porcentajes(codigo_curso)
            self.ui_mostrar_historial_asistencia()
        except ValueError as e:
             messagebox.showerror("Error", str(e))


    def ui_quitar_justificacion(self):
        if not self.verificar_logueo(): return
        sess_id, codigo_curso, rut_estudiante = self._get_selected_historial()
        if not sess_id: return
        
        datos_usuario = self.sistema._obtener_datos_usuario(self.user_id)
        sess = datos_usuario["sesiones"].get(sess_id)
        
        if rut_estudiante not in sess.ruts_justificados:
            messagebox.showwarning("No Justificado", "El alumno no tiene una inasistencia justificada en esta sesión.")
            return

        # Quitar de justificados (y no agregar a presentes para que quede como inasistente 'duro')
        nuevos_ruts_justificados = sess.ruts_justificados.copy()
        nuevos_ruts_justificados.remove(rut_estudiante)
        
        try:
            self.sistema.editar_sesion(self.user_id, sess_id, nuevos_ruts_justificados=nuevos_ruts_justificados)
            messagebox.showinfo("Éxito", "Justificación eliminada.")
            self.refrescar_lista_porcentajes(codigo_curso)
            self.ui_mostrar_historial_asistencia()
        except ValueError as e:
             messagebox.showerror("Error", str(e))


def main():
    sistema = SistemaAsistencia()
    app = AppGUI(sistema)
    app.mainloop()

if __name__ == "__main__":
    main()