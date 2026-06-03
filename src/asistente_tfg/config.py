"""
config.py — Configuración centralizada del sistema.

Todas las constantes de ruta, URL y nombre de modelo se definen aquí.
El resto de módulos importan desde este fichero en lugar de redefinirlas.
"""
import os

# Directorio raíz del proyecto (dos niveles por encima de src/asistente_tfg/)
_ESTE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(_ESTE_DIR))

# --- Rutas de datos ---
RUTA_BBDD_VECTORIAL = os.path.join(BASE_DIR, "Data", "database", "chroma_db_prueba")
DB_SQL = os.path.join(BASE_DIR, "Data", "database", "operacion.db")

# --- Servidor LLM (LM Studio) ---
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

# --- Modelo de embeddings ---
# paraphrase-multilingual-MiniLM-L12-v2: soporta 50 idiomas incluido el español.
# IMPORTANTE: debe coincidir exactamente con el modelo usado en los scripts de ingesta.
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
