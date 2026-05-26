import chromadb
from chromadb.utils import embedding_functions
import os

BASE_DIR = os.getcwd()
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")

print("Conectando a la base de datos en:", RUTA_BBDD_LOCAL)
client = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)

# Modelo multilingüe
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# Listar colecciones
colecciones = client.list_collections()
print(f"\nColecciones existentes ({len(colecciones)}):")
for col in colecciones:
    print(f" - {col.name}")

# Comprobar 'general_knowledge'
try:
    col_general = client.get_collection(name="general_knowledge", embedding_function=ef)
    count = col_general.count()
    print(f"\n[OK] Colección 'general_knowledge' encontrada.")
    print(f"     Total de documentos (chunks): {count}")
    if count > 0:
        peek = col_general.peek(limit=1)
        print("     Muestra de un documento:")
        print(f"       ID: {peek['ids'][0]}")
        print(f"       Metadatos: {peek['metadatas'][0]}")
        print(f"       Texto: {peek['documents'][0][:150]}...")
except Exception as e:
    print(f"\n[ERROR] No se pudo leer 'general_knowledge': {e}")

# Comprobar 'products_catalog'
try:
    col_prods = client.get_collection(name="products_catalog", embedding_function=ef)
    count = col_prods.count()
    print(f"\n[OK] Colección 'products_catalog' encontrada.")
    print(f"     Total de productos: {count}")
    if count > 0:
        peek = col_prods.peek(limit=1)
        print("     Muestra de un producto:")
        print(f"       ID: {peek['ids'][0]}")
        print(f"       Metadatos: {peek['metadatas'][0]}")
        print(f"       Texto vectorizado: {peek['documents'][0][:150]}...")
except Exception as e:
    print(f"\n[ERROR] No se pudo leer 'products_catalog': {e}")
