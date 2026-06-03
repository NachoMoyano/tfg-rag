"""
router.py — Enrutador semántico.

Clasifica la intención del usuario en una de las tres categorías del sistema
mediante Few-Shot Prompting con temperatura 0.0, garantizando determinismo
en la decisión de enrutamiento.

Categorías disponibles:
  - GENERAL           → consulta de conocimiento teórico
  - CATALOGO_BUSQUEDA → búsqueda de productos en el catálogo
  - CATALOGO_DETALLE  → detalle de un producto concreto
"""
import requests
from config import LM_STUDIO_URL

# Categoría aplicada cuando el LLM devuelve una etiqueta inválida o falla
CATEGORIA_FALLBACK = "CATALOGO_BUSQUEDA"

_PROMPT_TEMPLATE = """\
Clasifica la siguiente pregunta del usuario en UNA de estas TRES categorías exactas: \
'GENERAL', 'CATALOGO_BUSQUEDA' o 'CATALOGO_DETALLE'. \
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


def clasificar(pregunta: str) -> str:
    """
    Devuelve la categoría de intención para `pregunta`.

    Llama al LLM con temperatura 0.0 (determinismo total) y valida
    la respuesta contra las etiquetas permitidas. Si el modelo falla
    o devuelve una etiqueta inesperada, retorna CATEGORIA_FALLBACK.
    """
    payload = {
        "messages": [
            {"role": "user", "content": _PROMPT_TEMPLATE.format(pregunta=pregunta)}
        ],
        "temperature": 0.0,  # CRÍTICO: determinismo total en la clasificación
        "max_tokens": 10,    # Solo necesitamos una etiqueta
    }

    try:
        resp = requests.post(LM_STUDIO_URL, json=payload)
        resp.raise_for_status()
        decision = resp.json()["choices"][0]["message"]["content"].strip().upper()

        if "GENERAL" in decision:
            return "GENERAL"
        elif "DETALLE" in decision:
            return "CATALOGO_DETALLE"
        else:
            return "CATALOGO_BUSQUEDA"

    except Exception as e:
        print(f"⚠️  Enrutador: fallo al contactar con el LLM ({e}). Aplicando fallback.")
        return CATEGORIA_FALLBACK
