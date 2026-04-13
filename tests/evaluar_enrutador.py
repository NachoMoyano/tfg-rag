import requests
import time

# --- CONFIGURACIÓN ---
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

# --- LA FUNCIÓN A EVALUAR (Aislada) ---
def enrutador_semantico(pregunta):
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
z
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
        "temperature": 0.0, 
        "max_tokens": 10
    }
    
    try:
        resp = requests.post(LM_STUDIO_URL, json=payload)
        resp.raise_for_status()
        decision = resp.json()['choices'][0]['message']['content'].strip().upper()
        
        if "GENERAL" in decision: return "GENERAL"
        elif "DETALLE" in decision: return "CATALOGO_DETALLE"
        else: return "CATALOGO_BUSQUEDA"
    except Exception as e:
        return f"ERROR ({e})"

# --- EL DATASET DE EVALUACIÓN (20 Prompts + Ground Truth) ---
dataset_evaluacion = [
    # --- PRUEBAS: BÚSQUEDA / EXPLORACIÓN ---
    {"prompt": "Necesito un listado de productos sobre tráfico urbano.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "¿Qué datasets tenéis de la empresa DataRade?", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Busco información geográfica y mapas de Europa.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Muéstrame opciones relacionadas con el clima y la lluvia.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "¿Hay algo en el catálogo sobre transacciones financieras?", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Quiero ver qué tenéis de inteligencia artificial.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Fíltrame los datasets que sean de salud o medicina.", "truth": "CATALOGO_BUSQUEDA"},
    
    # --- PRUEBAS: DETALLE / ZOOM ---
    {"prompt": "Dame todas las características del producto EU POI Data.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Háblame más sobre la segunda opción de la tabla.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "¿Quién es el proveedor exacto del Spanish Labour Market y qué incluye?", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Quiero los detalles técnicos del dataset de Similarweb.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Amplía la información del último producto que mencionaste.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "¿Cuál es la descripción larga del pack de datos sintéticos?", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Analiza a fondo el producto número 3.", "truth": "CATALOGO_DETALLE"},
    
    # --- PRUEBAS: GENERAL / TEORÍA ---
    {"prompt": "Explícame el concepto de Data Mesh.", "truth": "GENERAL"},
    {"prompt": "¿Qué significa que un dataset esté anonimizado?", "truth": "GENERAL"},
    {"prompt": "Tengo una duda teórica: ¿qué es la latencia en la entrega de datos?", "truth": "GENERAL"},
    {"prompt": "Diferencias a nivel conceptual entre Data Warehouse y Data Lake.", "truth": "GENERAL"},
    {"prompt": "¿Cómo funciona el modelo de precios basado en consumo?", "truth": "GENERAL"},
    {"prompt": "Define qué es la gobernanza de datos.", "truth": "GENERAL"}
]

# --- MOTOR DE EVALUACIÓN ---
def ejecutar_evaluacion():
    print("Iniciando evaluación del Enrutador Semántico...\n")
    
    aciertos = 0
    total = len(dataset_evaluacion)
    resultados_detallados = []

    for i, test in enumerate(dataset_evaluacion, 1):
        pregunta = test["prompt"]
        verdad = test["truth"]
        
        print(f"Procesando {i}/{total}...", end="\r")
        
        # Llamada al LLM
        inicio = time.time()
        prediccion = enrutador_semantico(pregunta)
        fin = time.time()
        tiempo_ms = round((fin - inicio) * 1000)
        
        # Comprobar si ha acertado
        es_correcto = prediccion == verdad
        if es_correcto:
            aciertos += 1
            icono = "✅"
        else:
            icono = "❌"
            
        resultados_detallados.append({
            "prompt": pregunta,
            "esperado": verdad,
            "prediccion": prediccion,
            "icono": icono,
            "tiempo": tiempo_ms
        })

    # --- IMPRIMIR INFORME FINAL ---
    print(" " * 30, end="\r") # Limpiar línea de progreso
    print("-" * 70)
    print("INFORME DE RENDIMIENTO (BENCHMARK)")
    print("-" * 70)
    
    for r in resultados_detallados:
        if r['icono'] == '❌':
            # Imprimir los fallos en rojo/destacado si tu terminal lo soporta, aquí usamos texto claro
            print(f"{r['icono']} FALLO | Prompt: '{r['prompt']}'\n   ↳ Esperaba: {r['esperado']} | Predijo: {r['prediccion']} ({r['tiempo']}ms)\n")
        else:
            print(f"{r['icono']} OK    | Esperaba: {r['esperado']} | Predijo: {r['prediccion']} ({r['tiempo']}ms)")

    accuracy = (aciertos / total) * 100
    print("-" * 70)
    print(f"ACCURACY TOTAL: {aciertos}/{total} ({accuracy:.2f}%)")
    print("-" * 70)

if __name__ == "__main__":
    ejecutar_evaluacion()