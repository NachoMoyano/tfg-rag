# api_orquestador.py
from flask import Flask, request, jsonify
import chromadb
from chromadb.utils import embedding_functions
import requests
import sqlite3
import os

app = Flask(__name__)



directorio_actual = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(directorio_actual))
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")
DB_SQL = os.path.join(BASE_DIR, "Data", "database", "operacion.db")
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

# --- INICIALIZAR BBDD RELACIONAL (SQLite) ---
def init_sqlite():
    conn = sqlite3.connect(DB_SQL)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, rol TEXT, contenido TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs_sistema (id INTEGER PRIMARY KEY AUTOINCREMENT, nivel TEXT, mensaje TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_sqlite()

def guardar_mensaje(session_id, rol, contenido):
    conn = sqlite3.connect(DB_SQL)
    conn.execute("INSERT INTO historial_chat (session_id, rol, contenido) VALUES (?, ?, ?)", (session_id, rol, contenido))
    conn.commit()
    conn.close()

def obtener_historial(session_id, limite=4):
    conn = sqlite3.connect(DB_SQL)
    cursor = conn.cursor()
    cursor.execute("SELECT rol, contenido FROM historial_chat WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limite))
    filas = cursor.fetchall()
    conn.close()
    return [{"role": f[0], "content": f[1]} for f in reversed(filas)]

def guardar_log(nivel, mensaje):
    conn = sqlite3.connect(DB_SQL)
    conn.execute("INSERT INTO logs_sistema (nivel, mensaje) VALUES (?, ?)", (nivel, mensaje))
    conn.commit()
    conn.close()

# --- INICIALIZAR CHROMA (Las DOS colecciones) ---
print("Conectando a la Memoria Vectorial (ChromaDB)...")
client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Colecciones actualizadas
collection_general = client_chroma.get_collection(name="general_knowledge", embedding_function=ef)
collection_catalogo = client_chroma.get_collection(name="products_catalog", embedding_function=ef)
print("Memoria vectorial lista. (Conocimiento General y Catálogo cargados)")


def enrutador_semantico(pregunta):
    
    # Few-Shot Prompting para el LLM (Sin reglas if previas)
    prompt_router = f"""Clasifica la siguiente pregunta del usuario en UNA de estas TRES categorías exactas: 'GENERAL', 'CATALOGO_BUSQUEDA' o 'CATALOGO_DETALLE'. 
No devuelvas ningún otro texto, solo la etiqueta.

Ejemplo 1:
Pregunta: Busco datos de economía en España o mercado laboral.
Clasificación: CATALOGO_BUSQUEDA

Ejemplo 2:
Pregunta: ¿Qué diferencia hay entre usar una API REST o S3? Explícame la teoría.
Clasificación: GENERAL

Ejemplo 3:
Pregunta: Dame los detalles, características y proveedor del producto Synthetic Data Pack.
Clasificación: CATALOGO_DETALLE

Ejemplo 4:
Pregunta: ¿Tenéis algún dataset sobre el paro o pacientes de salud?
Clasificación: CATALOGO_BUSQUEDA

Ejemplo 5:
Pregunta: Quiero profundizar en la primera opción que me has dado.
Clasificación: CATALOGO_DETALLE

Ejemplo 6:
Pregunta: ¿Qué es la k-anonymity en privacidad de datos?
Clasificación: GENERAL

Pregunta: {pregunta}
Clasificación:"""
    
    payload = {
        "messages": [{"role": "user", "content": prompt_router}],
        "temperature": 0.0,  # CRÍTICO: Debe ser 0.0 para que tus futuras métricas sean deterministas y repetibles
        "max_tokens": 10     # Solo necesitamos una palabra
    }
    
    try:
        resp = requests.post(LM_STUDIO_URL, json=payload)
        resp.raise_for_status()
        
        # Limpiamos la respuesta por si el modelo añade puntos o espacios
        decision = resp.json()['choices'][0]['message']['content'].strip().upper()
        
        # Mapeo de seguridad final
        if "GENERAL" in decision: 
            return "GENERAL"
        elif "DETALLE" in decision: 
            return "CATALOGO_DETALLE"
        else:
            return "CATALOGO_BUSQUEDA" # Fallback por defecto si no es ninguna de las anteriores
            
    except Exception as e:
        print(f"❌ Aviso: Falló la conexión con el enrutador LLM ({e}).")
        return "CATALOGO_BUSQUEDA" # Fallback de seguridad en caso de caída del servidor


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    datos = request.json
    pregunta_usuario = datos.get("pregunta", "")
    session_id = datos.get("session_id", "anonimo") 

    if not pregunta_usuario:
        return jsonify({"error": "Pregunta vacía"}), 400

    historial_previo = obtener_historial(session_id)
    ruta_elegida = enrutador_semantico(pregunta_usuario)
    guardar_log("INFO", f"Enrutador decidió: {ruta_elegida}")
    print(f"El enrutador ha decidido buscar en: {ruta_elegida}", flush=True)

    contexto_texto = ""
    fuentes_visuales = ""

    # --- LÓGICA DE RECUPERACIÓN (EXPLOIT VS EXPLORE) ---
    if ruta_elegida == "GENERAL":
        results = collection_general.query(query_texts=[pregunta_usuario], n_results=3)
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                contexto_texto += f"- Fragmento {i+1}: {doc}\n"
        
        # Parche de seguridad para evitar Error 500 por desbordamiento de memoria
        LIMITE_CARACTERES = 6000
        if len(contexto_texto) > LIMITE_CARACTERES:
            contexto_texto = contexto_texto[:LIMITE_CARACTERES] + "\n\n... [NOTA: El contexto ha sido truncado por limite de memoria]."

        prompt_sistema = "Eres un Consultor Experto. Responde la duda teorica usando UNICAMENTE el contexto de la base de conocimiento proporcionada."
        fuentes_visuales = f"Busqueda Teorica\n\n{contexto_texto}"
    elif ruta_elegida == "CATALOGO_BUSQUEDA":
        results = collection_catalogo.query(query_texts=[pregunta_usuario], n_results=5)
        
        if results['metadatas'] and results['metadatas'][0]:
            for meta in results['metadatas'][0]:
                titulo = meta.get('titulo', 'N/A')
                proveedor = meta.get('proveedor', 'N/A')
                desc_corta = meta.get('descripcion_corta', 'N/A')
                contexto_texto += f"| {titulo} | {proveedor} | {desc_corta} |\n"
                
        prompt_sistema = """
            Eres un asistente de catálogo de datos. 
            Tu ÚNICA tarea es devolver una tabla Markdown con los productos que se te pasan en el contexto.
            La tabla debe tener 3 columnas: 'Título', 'Proveedor' y 'Descripción Corta'.
            No inventes datos. Si no hay proveedor, pon '-'. No añadas texto de introducción ni conclusión, SOLO la tabla.
       """
        fuentes_visuales = f"Explorando 5 productos del catálogo..."

    elif ruta_elegida == "CATALOGO_DETALLE":
            results = collection_catalogo.query(query_texts=[pregunta_usuario], n_results=1)
            
            if results['metadatas'] and results['metadatas'][0]:
                meta = results['metadatas'][0][0]
                
                # --- EL PARCHE DE SEGURIDAD DE MEMORIA ---
                desc_completa = str(meta.get('descripcion_larga', 'No disponible'))
                LIMITE_CARACTERES = 6000  # Límite estricto para que LM Studio no se congele
                
                if len(desc_completa) > LIMITE_CARACTERES:
                    desc_completa = desc_completa[:LIMITE_CARACTERES] + "\n\n... [NOTA: La descripción original ha sido truncada por límite de memoria]."
                
                contexto_texto = f"Título: {meta.get('titulo', 'N/A')}\nProveedor: {meta.get('proveedor', 'N/A')}\nDescripción Completa: {desc_completa}"
                
            prompt_sistema = "Eres un analista de datos. El usuario quiere detalles de un producto. Proporciona un resumen exhaustivo y bien estructurado (con viñetas o apartados) de las características de este producto basándote en la Descripción Completa proporcionada en el contexto."
            fuentes_visuales = f"Extrayendo detalles de: {meta.get('titulo', 'N/A')}"

    # --- GENERACIÓN DE RESPUESTA ---
    mensaje_aumentado = f"CONTEXTO RECUPERADO:\n{contexto_texto}\n\nPREGUNTA DEL USUARIO:\n{pregunta_usuario}"
    
    mensajes_llm = [{"role": "system", "content": prompt_sistema}]
    mensajes_llm.extend(historial_previo) 
    mensajes_llm.append({"role": "user", "content": mensaje_aumentado}) 

    payload = {"messages": mensajes_llm, "temperature": 0.3, "max_tokens": 1500}

    try:
        respuesta_lm = requests.post(LM_STUDIO_URL, json=payload)
        respuesta_lm.raise_for_status()
        texto_generado = respuesta_lm.json()['choices'][0]['message']['content']
        
        guardar_mensaje(session_id, "user", pregunta_usuario) 
        guardar_mensaje(session_id, "assistant", texto_generado)
        
        return jsonify({"respuesta": texto_generado, "documentos_usados": fuentes_visuales})

    except Exception as e:
        guardar_log("ERROR", f"Fallo al conectar con LLM: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)