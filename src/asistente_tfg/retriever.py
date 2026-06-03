"""
retriever.py — Módulo de recuperación (ChromaDB).

Gestiona la conexión con la base de datos vectorial e implementa la lógica
de recuperación por categoría. Expone una única función pública
(recuperar_contexto) que, dada una pregunta y su categoría, devuelve el
contexto recuperado, las fuentes para la UI y el prompt de sistema adaptado.

La inicialización de ChromaDB se realiza una sola vez al importar el módulo,
de forma que la conexión persiste durante toda la vida del servidor.
"""
import chromadb
from chromadb.utils import embedding_functions
from config import RUTA_BBDD_VECTORIAL, EMBEDDING_MODEL

# ---------------------------------------------------------------------------
# Inicialización de ChromaDB (se ejecuta una sola vez al arrancar el servidor)
# ---------------------------------------------------------------------------
print("Conectando a la Memoria Vectorial (ChromaDB)...")
_client = chromadb.PersistentClient(path=RUTA_BBDD_VECTORIAL)
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
_col_general  = _client.get_collection(name="general_knowledge",  embedding_function=_ef)
_col_catalogo = _client.get_collection(name="products_catalog",   embedding_function=_ef)
print("Memoria vectorial lista. (Conocimiento General y Catálogo cargados)")

# Límite de caracteres aplicado al contexto inyectado en el prompt
# (evita desbordamientos de memoria en la GPU al exceder la ventana de contexto)
_LIMITE_CHARS = 6_000

# Configuración de recuperación por categoría: colección y número de resultados
_CONFIG_RECUPERACION = {
    "GENERAL":           {"coleccion": _col_general,  "n_results": 3},
    "CATALOGO_BUSQUEDA": {"coleccion": _col_catalogo, "n_results": 5},
    "CATALOGO_DETALLE":  {"coleccion": _col_catalogo, "n_results": 1},
}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def recuperar_contexto(pregunta: str, categoria: str) -> dict:
    """
    Consulta ChromaDB según la categoría y construye el contexto del prompt.

    Parámetros
    ----------
    pregunta  : texto original del usuario
    categoria : una de GENERAL | CATALOGO_BUSQUEDA | CATALOGO_DETALLE

    Retorna
    -------
    dict con las claves:
      - contexto_texto   : texto inyectado en el prompt aumentado
      - fuentes_visuales : etiqueta legible para mostrar en la UI
      - prompt_sistema   : instrucciones de sistema adaptadas a la categoría
    """
    cfg = _CONFIG_RECUPERACION.get(categoria, _CONFIG_RECUPERACION["CATALOGO_BUSQUEDA"])
    results = cfg["coleccion"].query(query_texts=[pregunta], n_results=cfg["n_results"])

    contexto_texto   = ""
    fuentes_visuales = ""
    prompt_sistema   = ""

    # --- GENERAL: fragmentos de la base de conocimiento teórico ---
    if categoria == "GENERAL":
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                contexto_texto += f"- Fragmento {i + 1}: {doc}\n"

        if len(contexto_texto) > _LIMITE_CHARS:
            contexto_texto = (
                contexto_texto[:_LIMITE_CHARS]
                + "\n\n... [NOTA: El contexto ha sido truncado por límite de memoria]."
            )

        prompt_sistema = (
            "Eres un Consultor Experto. Responde la duda teórica usando ÚNICAMENTE "
            "el contexto de la base de conocimiento proporcionada."
        )
        fuentes_visuales = f"Búsqueda Teórica\n\n{contexto_texto}"

    # --- CATALOGO_BUSQUEDA: tabla de hasta 5 productos relevantes ---
    elif categoria == "CATALOGO_BUSQUEDA":
        if results["metadatas"] and results["metadatas"][0]:
            for meta in results["metadatas"][0]:
                titulo    = meta.get("titulo",           "N/A")
                proveedor = meta.get("proveedor",        "N/A")
                desc_corta = meta.get("descripcion_corta", "N/A")
                contexto_texto += f"| {titulo} | {proveedor} | {desc_corta} |\n"

        prompt_sistema = (
            "Eres un asistente de catálogo de datos. "
            "Tu ÚNICA tarea es devolver una tabla Markdown con los productos que se te pasan en el contexto. "
            "La tabla debe tener 3 columnas: 'Título', 'Proveedor' y 'Descripción Corta'. "
            "No inventes datos. Si no hay proveedor, pon '-'. "
            "No añadas texto de introducción ni conclusión, SOLO la tabla."
        )
        fuentes_visuales = "Explorando 5 productos del catálogo..."

    # --- CATALOGO_DETALLE: ficha completa del producto más relevante ---
    elif categoria == "CATALOGO_DETALLE":
        if results["metadatas"] and results["metadatas"][0]:
            meta = results["metadatas"][0][0]
            desc_completa = str(meta.get("descripcion_larga", "No disponible"))

            if len(desc_completa) > _LIMITE_CHARS:
                desc_completa = (
                    desc_completa[:_LIMITE_CHARS]
                    + "\n\n... [NOTA: La descripción ha sido truncada por límite de memoria]."
                )

            contexto_texto = (
                f"Título: {meta.get('titulo', 'N/A')}\n"
                f"Proveedor: {meta.get('proveedor', 'N/A')}\n"
                f"Descripción Completa: {desc_completa}"
            )
            fuentes_visuales = f"Extrayendo detalles de: {meta.get('titulo', 'N/A')}"

        prompt_sistema = (
            "Eres un analista de datos. El usuario quiere detalles de un producto. "
            "Proporciona un resumen exhaustivo y bien estructurado (con viñetas o apartados) "
            "de las características de este producto basándote en la Descripción Completa proporcionada."
        )

    return {
        "contexto_texto":   contexto_texto,
        "fuentes_visuales": fuentes_visuales,
        "prompt_sistema":   prompt_sistema,
    }
