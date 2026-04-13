import chromadb
from chromadb.utils import embedding_functions
import uuid
import os

# --- CONFIGURACIÓN ---

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVO_MD = os.path.join(BASE_DIR, "Data", "knowledge_base", "DataSharingKB.md")
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")
print("Conectando a ChromaDB...")
client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Creamos una NUEVA colección (o la recuperamos si ya existe)
collection_general = client_chroma.get_or_create_collection(
    name="general_knowledge", 
    embedding_function=ef
)

print(f"Leyendo el archivo {ARCHIVO_MD}...")

try:
    with open(ARCHIVO_MD, 'r', encoding='utf-8') as f:
        texto_completo = f.read()

    fragmentos = texto_completo.split("\n## ")
    
    documentos = []
    metadatos = []
    ids = []

    for i, fragmento in enumerate(fragmentos):
        # Limpiamos espacios en blanco
        chunk_limpio = fragmento.strip()
        if not chunk_limpio:
            continue
            
        if i > 0 and not chunk_limpio.startswith("#"):
            chunk_limpio = "## " + chunk_limpio
            
        documentos.append(chunk_limpio)
        metadatos.append({"source": ARCHIVO_MD, "tipo": "teoria"})
        ids.append(f"teoria_{uuid.uuid4().hex[:8]}") # ID único aleatorio

    # --- INSERCIÓN EN CHROMA ---
    print(f"Insertando {len(documentos)} fragmentos de conocimiento en ChromaDB...")
    collection_general.add(
        documents=documentos,
        metadatas=metadatos,
        ids=ids
    )

    print("¡Ingesta completada! La colección 'general_knowledge' ya está lista.")

except FileNotFoundError:
    print(f"Error: No se ha encontrado el archivo {ARCHIVO_MD}. Asegúrate de que esté en la misma carpeta.")
except Exception as e:
    print(f"Error inesperado: {e}")