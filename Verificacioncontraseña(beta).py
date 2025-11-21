import re  # Importamos el módulo 're' (Expresiones Regulares).
# Es una herramienta muy potente para buscar patrones específicos de texto
# (como "buscar si hay un número" o "buscar si hay un símbolo").

def validar_contrasena(password): #Esto es para validar contraseña (obviamente)
    """
    Función que recibe una contraseña y verifica si cumple las reglas.
    Devuelve dos valores:
    1. Un valor Booleano (True o False) indicando si pasó la prueba.
    2. Una lista de mensajes (errores encontrados o mensaje de éxito).
    """
    
    # PASO 1: Crear una lista vacía para acumular los errores.
    # Si al final esta lista sigue vacía, significa que la contraseña es perfecta.
    errores = []

    # PASO 2: Verificar la longitud.
    # len(password) cuenta cuántos caracteres tiene el texto.
    if len(password) < 8:
        errores.append("❌ Error: La contraseña es muy corta (mínimo 8 caracteres).")

    # PASO 3: Verificar si hay números.
    # re.search busca el patrón dentro del texto.
    # r"\d" es el código de Regex que significa "Cualquier dígito del 0 al 9".
    if not re.search(r"\d", password):
        errores.append("❌ Error: Falta al menos un número (0-9).")

    # PASO 4: Verificar mayúsculas.
    # [A-Z] busca cualquier letra desde la A hasta la Z en mayúscula.
    if not re.search(r"[A-Z]", password):
        errores.append("❌ Error: Falta al menos una letra mayúscula.")

    # PASO 5: Verificar minúsculas.
    # [a-z] busca cualquier letra desde la a hasta la z en minúscula.
    if not re.search(r"[a-z]", password):
        errores.append("❌ Error: Falta al menos una letra minúscula.")

    # PASO 6: Verificar símbolos especiales (El paso más importante para tu petición).
    # Aquí definimos un conjunto de caracteres aceptados como símbolos dentro de los corchetes [ ].
    # Incluye: ! @ # $ % ^ & * ( ) _ + etc.
    patron_simbolos = r"[ !#$%&'()*+,-./:;<=>?@[\\\]^_`{|}~]"
    
    if not re.search(patron_simbolos, password):
        errores.append("❌ Error: Falta al menos un símbolo especial (ej: @, #, $, %).")

    # PASO 7: Evaluación final.
    # Si la longitud de la lista 'errores' es mayor a 0, hay fallos.
    if len(errores) > 0:
        return False, errores  # Devolvemos False y la lista de problemas.
    else:
        return True, ["✅ ¡Excelente! Contraseña segura y aceptada."] # Devolvemos True y mensaje de éxito.

# --- BLOQUE PRINCIPAL (Main) ---
# Esta parte solo se ejecuta si corres el archivo directamente.
if __name__ == "__main__":
    print("--- 🔐 VALIDADOR DE CONTRASEÑAS 🔐 ---")
    print("Instrucciones: Usa mayúsculas, minúsculas, números y símbolos.\n")

    # Usamos un bucle 'while True' para pedir la contraseña infinitamente
    # hasta que el usuario ingrese una correcta.
    while True:
        # Solicitamos la entrada del usuario
        entrada_usuario = input(">> Por favor, crea tu contraseña: ")
        
        # Llamamos a nuestra función de validación
        # Desempaquetamos el resultado en dos variables: 'es_valida' y 'mensajes'
        es_valida, mensajes = validar_contrasena(entrada_usuario)

        # Si es válida, mostramos éxito y rompemos el bucle (break)
        if es_valida:
            print(mensajes[0]) # Imprime el mensaje de éxito
            break 
        
        # Si NO es válida, mostramos los errores encontrados
        else:
            print("\n⚠️ Tu contraseña no es segura:")
            for mensaje in mensajes:
                print(mensaje) # Imprime cada error de la lista uno por uno
            print("-" * 30) # Una línea separadora para que se vea ordenado

            print("Inténtalo de nuevo.\n")
