# ingesta.py — VERSIÓN MEJORADA
# Mejoras aplicadas:
#   1. Modelo de embeddings multilingüe (soporta español)
#   2. Chunking con control de tamaño máximo y solapamiento
#   3. Limpieza de símbolos Markdown antes de vectorizar
#   4. Filtrado de chunks demasiado cortos

import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import re

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVO_MD = os.path.join(BASE_DIR, "Data", "knowledge_base", "DataSharingKB.md")
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")

# Parámetros de chunking
MAX_CHARS_CHUNK = 800   # Tamaño máximo de cada fragmento en caracteres
SOLAPAMIENTO = 150      # Caracteres que se comparten entre fragmentos consecutivos
MIN_CHARS_CHUNK = 100   # Fragmentos más cortos que esto se descartan


# --- FUNCIONES DE PROCESAMIENTO ---

def limpiar_markdown(texto):
    """Elimina símbolos de formato Markdown para que el embedding se centre en el contenido."""
    texto = re.sub(r'#{1,6}\s*', '', texto)                       # Cabeceras ## ### etc.
    texto = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)          # **negrita** y *cursiva*
    texto = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', texto)              # [links](url)
    texto = re.sub(r'`{1,3}.*?`{1,3}', '', texto, flags=re.DOTALL) # `código`
    texto = re.sub(r'[-*_]{3,}', '', texto)                        # Líneas horizontales ---
    texto = re.sub(r'>\s?', '', texto)                             # Citas >
    texto = re.sub(r'\n{3,}', '\n\n', texto)                       # Saltos de línea excesivos
    return texto.strip()


def chunkear_con_solapamiento(texto, max_chars=MAX_CHARS_CHUNK, solapamiento=SOLAPAMIENTO):
    """
    Divide un texto en fragmentos de max_chars caracteres con solapamiento.
    Intenta cortar en puntos naturales (punto, salto de línea) para no partir frases.
    """
    chunks = []
    inicio = 0

    while inicio < len(texto):
        fin = inicio + max_chars
        chunk = texto[inicio:fin]

        # Si no es el último chunk, intentamos cortar en un punto natural
        if fin < len(texto):
            ultimo_corte = max(chunk.rfind('. '), chunk.rfind('\n'))
            if ultimo_corte > max_chars // 2:  # Solo si el corte está en la mitad o más
                fin = inicio + ultimo_corte + 1
                chunk = texto[inicio:fin]

        chunk_limpio = chunk.strip()
        if chunk_limpio:
            chunks.append(chunk_limpio)

        inicio = fin - solapamiento  # Retrocedemos 'solapamiento' chars para el siguiente

    return chunks


# --- CONEXIÓN A CHROMADB ---
print("Conectando a ChromaDB...")
client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)

# MEJORA 1: Modelo multilingüe en lugar de all-MiniLM-L6-v2 (solo inglés)
# paraphrase-multilingual-MiniLM-L12-v2 soporta 50 idiomas incluyendo español
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# Creamos o recuperamos la colección de conocimiento general
collection_general = client_chroma.get_or_create_collection(
    name="general_knowledge",
    embedding_function=ef
)

print(f"Leyendo el archivo {ARCHIVO_MD}...")

try:
    with open(ARCHIVO_MD, 'r', encoding='utf-8') as f:
        texto_completo = f.read()

    # Dividimos primero por secciones principales (##)
    secciones = texto_completo.split("\n## ")

    documentos = []
    metadatos = []
    ids = []
    chunks_descartados = 0

    for i, seccion in enumerate(secciones):
        seccion_limpia = seccion.strip()
        if not seccion_limpia:
            continue

        # Restauramos el ## que quitó el split (excepto en la primera sección)
        if i > 0 and not seccion_limpia.startswith("#"):
            seccion_limpia = "## " + seccion_limpia

        # MEJORA 2: Control de tamaño — si la sección es pequeña la usamos tal cual,
        # si es grande la troceamos con solapamiento
        if len(seccion_limpia) <= MAX_CHARS_CHUNK:
            sub_chunks = [seccion_limpia]
        else:
            sub_chunks = chunkear_con_solapamiento(seccion_limpia)

        for j, chunk in enumerate(sub_chunks):
            # MEJORA 4: Filtrar chunks demasiado cortos
            if len(chunk) < MIN_CHARS_CHUNK:
                chunks_descartados += 1
                continue

            # MEJORA 3: Limpiamos el Markdown para el vector, guardamos el original en metadatos
            texto_para_vector = limpiar_markdown(chunk)

            documentos.append(texto_para_vector)
            metadatos.append({
                "source": ARCHIVO_MD,
                "tipo": "teoria",
                "seccion_idx": i,
                "sub_chunk_idx": j,
                "texto_original": chunk  # Guardamos el original con formato para mostrarlo al usuario
            })
            ids.append(f"teoria_{uuid.uuid4().hex[:8]}")

    # --- INSERCIÓN EN CHROMA ---
    print(f"Insertando {len(documentos)} fragmentos en ChromaDB...")
    print(f"  (Chunks descartados por ser demasiado cortos: {chunks_descartados})")

    collection_general.add(
        documents=documentos,
        metadatas=metadatos,
        ids=ids
    )

    print("¡Ingesta completada! La colección 'general_knowledge' ya está lista.")

except FileNotFoundError:
    print(f"Error: No se ha encontrado el archivo {ARCHIVO_MD}.")
except Exception as e:
    print(f"Error inesperado: {e}")

