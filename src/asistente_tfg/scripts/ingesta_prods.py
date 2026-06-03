# ingesta_prods.py — VERSIÓN MEJORADA
# Mejoras aplicadas:
#   1. Modelo de embeddings multilingüe (soporta español)
#   2. Texto vectorizable enriquecido con resumen de la descripción larga
#   3. Limpieza básica de texto antes de vectorizar
#   4. Filtrado de productos con datos insuficientes

import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ARCHIVO_EXCEL = os.path.join(BASE_DIR, "Data", "raw", "miguel_descriptions.xlsx")
RUTA_BBDD_LOCAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")
NOMBRE_COLECCION = "products_catalog"

# Cuántos caracteres de la descripción larga incluimos en el vector de búsqueda
CHARS_DESC_LARGA_EN_VECTOR = 300


def limpiar_texto(texto):
    """Limpieza básica de texto para mejorar la calidad del embedding."""
    if not texto or texto == 'nan':
        return ''
    # Eliminar símbolos Markdown residuales
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)
    texto = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', texto)
    # Normalizar espacios y saltos de línea
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)
    return texto.strip()


def ingestar_catalogo():
    print("Conectando a ChromaDB...")
    client_chroma = chromadb.PersistentClient(path=RUTA_BBDD_LOCAL)

    # MEJORA 1: Modelo multilingüe — debe coincidir con el usado en ingesta.py y api_orquestador.py
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    # Borramos la colección anterior para evitar duplicados
    try:
        client_chroma.delete_collection(name=NOMBRE_COLECCION)
        print(f"Colección '{NOMBRE_COLECCION}' anterior borrada.")
    except Exception:
        print(f"Creando nueva colección '{NOMBRE_COLECCION}'...")

    collection_catalogo = client_chroma.create_collection(
        name=NOMBRE_COLECCION,
        embedding_function=ef
    )

    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"Error: No se encuentra el archivo en la ruta: {ARCHIVO_EXCEL}")
        return

    print(f"Leyendo el archivo Excel: {ARCHIVO_EXCEL}...")

    try:
        df = pd.read_excel(ARCHIVO_EXCEL)

        documentos_busqueda = []
        metadatos_payload = []
        ids_unicos = []
        productos_descartados = 0

        for index, row in df.iterrows():
            proveedor = limpiar_texto(str(row.get('Marketplace', '')))
            titulo = limpiar_texto(str(row.get('Título', '')))
            desc_corta = limpiar_texto(str(row.get('Descripción corta', '')))
            desc_larga = limpiar_texto(str(row.get('Descripción larga', '')))

            # MEJORA 4: Descartamos productos sin título ni descripción (datos insuficientes)
            if not titulo or not desc_corta:
                productos_descartados += 1
                continue

            # MEJORA 2: Enriquecemos el vector con las primeras N chars de la descripción larga.
            # Así la búsqueda semántica también cubre características técnicas detalladas.
            desc_larga_resumen = desc_larga[:CHARS_DESC_LARGA_EN_VECTOR] if desc_larga else ''

            texto_vector = (
                f"Título: {titulo}. "
                f"Proveedor: {proveedor}. "
                f"Resumen: {desc_corta}. "
                f"Detalles: {desc_larga_resumen}"
            )

            documentos_busqueda.append(texto_vector)

            # Los metadatos siguen guardando la descripción larga completa para el LLM
            metadatos_payload.append({
                "proveedor": proveedor,
                "titulo": titulo,
                "descripcion_corta": desc_corta,
                "descripcion_larga": desc_larga
            })

            ids_unicos.append(f"prod_{uuid.uuid4().hex[:8]}")

        # --- INSERCIÓN EN CHROMA POR LOTES ---
        total_productos = len(documentos_busqueda)
        tamano_lote = 5000

        print(f"Insertando {total_productos} productos en ChromaDB en lotes de {tamano_lote}...")
        print(f"  (Productos descartados por datos insuficientes: {productos_descartados})")

        for i in range(0, total_productos, tamano_lote):
            fin = min(i + tamano_lote, total_productos)
            print(f"   -> Procesando lote del {i} al {fin}...")
            collection_catalogo.add(
                documents=documentos_busqueda[i:fin],
                metadatas=metadatos_payload[i:fin],
                ids=ids_unicos[i:fin]
            )

        print("¡Ingesta del catálogo completada con éxito!")

    except Exception as e:
        print(f"Error inesperado durante el procesamiento: {e}")


if __name__ == "__main__":
    ingestar_catalogo()

