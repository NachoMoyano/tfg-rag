import chromadb
from chromadb.utils import embedding_functions

# --- CONFIGURACIÓN ---
RUTA_BBDD_LOCAL = "./chroma_db_prueba"
NOMBRE_COLECCION = "products_catalog"

print("🔌 Conectando a ChromaDB...")
client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

try:
    # 1. Obtenemos la colección
    coleccion = client_chroma.get_collection(name=NOMBRE_COLECCION, embedding_function=ef)
    
    # 2. Contamos cuántos registros hay exactamente
    total_productos = coleccion.count()
    print(f"TOTAL DE REGISTROS: {total_productos}")
    
    if total_productos > 0:
        print("ECHANDO UN VISTAZO A LOS 2 PRIMEROS PRODUCTOS (Peek):")
        # peek(2) nos devuelve los 2 primeros registros sin tener que buscar nada
        muestra = coleccion.peek(2) 
        
        for i in range(len(muestra['ids'])):
            print(f"\n🔹 ID: {muestra['ids'][i]}")
            print(f"DOCUMENTO (Lo que lee el buscador): {muestra['documents'][i]}")
            print(f"METADATOS (Lo que le pasamos al LLM):")
            # Imprimimos los metadatos bonitos
            for clave, valor in muestra['metadatas'][i].items():
                print(f"   - {clave}: {str(valor)[:100]}...") # Cortamos a 100 caracteres para no inundar la pantalla
                
except Exception as e:
    print(f"\nError al acceder a la colección: {e}")