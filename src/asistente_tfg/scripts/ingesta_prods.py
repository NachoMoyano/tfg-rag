import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVO_EXCEL = os.path.join(BASE_DIR, "Data", "raw", "miguel_descriptions.xlsx")
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")
NOMBRE_COLECCION = "products_catalog"

def ingestar_catalogo():
    print("Conectando a ChromaDB...")
    client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)
    
    # Usamos el mismo modelo de embeddings que para el conocimiento general
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    # --- 2. PREPARAR LA COLECCIÓN ---
    # Borramos la colección si ya existía para evitar duplicados al hacer pruebas
    try:
        client_chroma.delete_collection(name=NOMBRE_COLECCION)
        print(f"Colección '{NOMBRE_COLECCION}' anterior borrada.")
    except Exception:
        print(f"Creando nueva colección '{NOMBRE_COLECCION}'...")

    collection_catalogo = client_chroma.create_collection(
        name=NOMBRE_COLECCION, 
        embedding_function=ef
    )

    # --- 3. LEER EL EXCEL Y PROCESAR ---
    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"Error: No se encuentra el archivo en la ruta: {ARCHIVO_EXCEL}")
        return

    print(f"Leyendo el archivo Excel: {ARCHIVO_EXCEL}...")
    try:
        # pip install pandas openpyxl (si te da error de librerías)
        df = pd.read_excel(ARCHIVO_EXCEL)
        
        documentos_busqueda = []
        metadatos_payload = []
        ids_unicos = []

        # Recorremos cada fila de tu Excel
        for index, row in df.iterrows():
            # Usamos .get() por si alguna columna tiene un nombre ligeramente distinto o falta
            proveedor = str(row.get('Marketplace', ''))
            titulo = str(row.get('Título', ''))
            desc_corta = str(row.get('Descripción corta', ''))
            desc_larga = str(row.get('Descripción larga', ''))

            # A. EL DOCUMENTO DE BÚSQUEDA (Optimizado para el motor vectorial)
            texto_vector = f"Título: {titulo}. Proveedor: {proveedor}. Resumen: {desc_corta}"
            documentos_busqueda.append(texto_vector)

            # B. LOS METADATOS (Toda la carga útil para el LLM)
            metadato = {
                "proveedor": proveedor,
                "titulo": titulo,
                "descripcion_corta": desc_corta,
                "descripcion_larga": desc_larga
            }
            metadatos_payload.append(metadato)
            
            # C. ID ÚNICO
            ids_unicos.append(f"prod_{uuid.uuid4().hex[:8]}")

        # --- 4. INSERCIÓN EN CHROMA (POR LOTES) ---
        total_productos = len(documentos_busqueda)
        tamano_lote = 5000  # Un número seguro por debajo del límite de 5461

        print(f"Insertando {total_productos} productos en ChromaDB en lotes de {tamano_lote}...")

        for i in range(0, total_productos, tamano_lote):
            # Calculamos el final de este lote
            fin = min(i + tamano_lote, total_productos)
            
            print(f"   -> Procesando lote del {i} al {fin}...")
            
            collection_catalogo.add(
                documents=documentos_busqueda[i:fin],
                metadatas=metadatos_payload[i:fin],
                ids=ids_unicos[i:fin]
            )

        print("¡Ingesta del catálogo masivo completada con éxito!")

    except Exception as e:
        print(f"Error inesperado durante el procesamiento: {e}")

if __name__ == "__main__":
    ingestar_catalogo() 