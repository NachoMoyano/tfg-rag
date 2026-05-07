import requests
import time
import json
import os

# Configuracion
API_URL = "http://localhost:5000/chat"
OUTPUT_FILE = "resultados_laboratorio.json"

dataset_pruebas = [
    # --- BLOQUE 1: CONCEPTOS GENERALES (GENERAL) ---
    {"id": 1, "pregunta": "Explícame el concepto de Data Mesh.", "categoria": "GENERAL"},
    {"id": 2, "pregunta": "¿Qué significa que un dataset esté anonimizado?", "categoria": "GENERAL"},
    {"id": 3, "pregunta": "Diferencias técnicas entre Data Warehouse y Data Lake.", "categoria": "GENERAL"},
    {"id": 4, "pregunta": "Define el modelo de precios de suscripción (Subscription-based).", "categoria": "GENERAL"},
    {"id": 5, "pregunta": "¿Cómo funciona el modelo de precios One-off?", "categoria": "GENERAL"},
    {"id": 6, "pregunta": "Explícame qué son los productos de datos basados en volumen (pay-as-you-go).", "categoria": "GENERAL"},
    {"id": 7, "pregunta": "¿Por qué es importante la gobernanza de datos?", "categoria": "GENERAL"},
    {"id": 8, "pregunta": "¿Qué es la latencia en la entrega de datos?", "categoria": "GENERAL"},
    {"id": 9, "pregunta": "Diferencia entre datos estructurados y no estructurados.", "categoria": "GENERAL"},
    {"id": 10, "pregunta": "¿Qué es la k-anonymity en privacidad de datos?", "categoria": "GENERAL"},
    {"id": 11, "pregunta": "Define el concepto de API REST para consumo de datos.", "categoria": "GENERAL"},
    {"id": 12, "pregunta": "¿Qué es el Data Sharing o intercambio de datos?", "categoria": "GENERAL"},
    {"id": 13, "pregunta": "Explica la importancia de los datos ESG en el sector corporativo.", "categoria": "GENERAL"},
    {"id": 14, "pregunta": "¿Qué significa PHI en el contexto de datos de salud?", "categoria": "GENERAL"},
    {"id": 15, "pregunta": "¿Qué es un Identity Graph?", "categoria": "GENERAL"},

    # --- BLOQUE 2: BÚSQUEDA Y EXPLORACIÓN (CATALOGO_BUSQUEDA) ---
    {"id": 16, "pregunta": "Busco datos de economía en España o mercado laboral.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 17, "pregunta": "Fíltrame los datasets que sean de salud o medicina.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 18, "pregunta": "Necesito un listado de productos sobre tráfico urbano y automoción.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 19, "pregunta": "¿Qué datasets tenéis de la empresa DataRade?", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 20, "pregunta": "Muéstrame opciones relacionadas con el clima y el medio ambiente.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 21, "pregunta": "¿Hay algo en el catálogo sobre transacciones financieras o banca?", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 22, "pregunta": "Quiero ver qué tenéis sobre videojuegos y gaming.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 23, "pregunta": "Busco datos para entrenar modelos de Inteligencia Artificial.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 24, "pregunta": "¿Tenéis catálogos de recursos naturales o minería?", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 25, "pregunta": "Muéstrame datasets del sector público o gobierno.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 26, "pregunta": "Busco información sobre retail, supermercados o marketing.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 27, "pregunta": "Listado de datasets de telecomunicaciones e IoT.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 28, "pregunta": "¿Qué productos ofrece el proveedor Snowflake?", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 29, "pregunta": "Quiero ver datos de medios de comunicación y entretenimiento.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 30, "pregunta": "Busco datos de manufactura, industria o cadena de suministro.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 31, "pregunta": "Recomiéndame datasets geográficos de Europa.", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 32, "pregunta": "¿Tenéis datos sintéticos de pacientes?", "categoria": "CATALOGO_BUSQUEDA"},
    {"id": 33, "pregunta": "Busco información de prescripciones farmacéuticas.", "categoria": "CATALOGO_BUSQUEDA"},

    # --- BLOQUE 3: DETALLES DE PRODUCTO (CATALOGO_DETALLE) ---
    {"id": 34, "pregunta": "Dame todas las características del producto EU POI Data.", "categoria": "CATALOGO_DETALLE"},
    {"id": 35, "pregunta": "¿Quién es el proveedor exacto del Spanish Labour Market y qué incluye?", "categoria": "CATALOGO_DETALLE"},
    {"id": 36, "pregunta": "¿Qué taxonomías utiliza el Spanish Labour Market Dataset?", "categoria": "CATALOGO_DETALLE"},
    {"id": 37, "pregunta": "Quiero los detalles del Synthetic Data Pack de 1000 pacientes con 1 año de datos.", "categoria": "CATALOGO_DETALLE"},
    {"id": 38, "pregunta": "Amplía la información sobre Open Pharmacy Prescribing and Dispensing Data.", "categoria": "CATALOGO_DETALLE"},
    {"id": 39, "pregunta": "¿Qué regiones geográficas cubre exactamente el dataset EU POI Data?", "categoria": "CATALOGO_DETALLE"},
    {"id": 40, "pregunta": "Detalla las limitaciones o restricciones de uso de los datos sintéticos de pacientes.", "categoria": "CATALOGO_DETALLE"},
    {"id": 41, "pregunta": "¿El Spanish Labour Market incluye datos de salario? Dame los detalles.", "categoria": "CATALOGO_DETALLE"},
    {"id": 42, "pregunta": "Explícame qué campos exactos trae el dataset de puntos de interés de España.", "categoria": "CATALOGO_DETALLE"},
    {"id": 43, "pregunta": "¿Hay algún contacto de ventas para el dataset de Lightcast?", "categoria": "CATALOGO_DETALLE"},
    {"id": 44, "pregunta": "Dame un resumen exhaustivo del DataSource Consumer Health Data.", "categoria": "CATALOGO_DETALLE"},
    {"id": 45, "pregunta": "¿Qué significa ESCO e ISCO08 dentro del contexto del dataset laboral español?", "categoria": "CATALOGO_DETALLE"},
    {"id": 46, "pregunta": "Quiero saber el nivel de granularidad del dataset de salud de Snowflake.", "categoria": "CATALOGO_DETALLE"},
    {"id": 47, "pregunta": "Dime los casos de uso recomendados para el dataset de negocios en España de DataRade.", "categoria": "CATALOGO_DETALLE"},
    {"id": 48, "pregunta": "¿Cuántos años de historial tiene el pack sintético más grande de AWS?", "categoria": "CATALOGO_DETALLE"},
    {"id": 49, "pregunta": "Detalles del proveedor Techsalerator en el contexto de datos POI.", "categoria": "CATALOGO_DETALLE"},
    {"id": 50, "pregunta": "Resumen técnico completo del dataset de ofertas de empleo en España.", "categoria": "CATALOGO_DETALLE"}
]

def estimar_tokens(texto):
    return len(texto) / 4

def ejecutar_pruebas():
    print("Iniciando fase de captura de datos en laboratorio...")
    resultados = []

    for item in dataset_pruebas:
        print(f"Procesando ID {item['id']}: {item['pregunta']}")
        
        payload = {
            "pregunta": item["pregunta"],
            "session_id": f"lab_test_{item['id']}"
        }
        
        inicio = time.time()
        try:
            # Timeout extendido para evitar cortes en inferencia local
            resp = requests.post(API_URL, json=payload, timeout=300)
            fin = time.time()
            
            if resp.status_code == 200:
                data = resp.json()
                latencia = fin - inicio
                texto_resp = data.get("respuesta", "")
                tps = estimar_tokens(texto_resp) / latencia
                
                resultados.append({
                    "id": item["id"],
                    "pregunta": item["pregunta"],
                    "respuesta": texto_resp,
                    "contexto": data.get("documentos_usados", ""),
                    "latencia": round(latencia, 2),
                    "tps": round(tps, 2),
                    "estado": "OK"
                })
            else:
                resultados.append({"id": item["id"], "pregunta": item["pregunta"], "estado": f"ERROR_{resp.status_code}"})
                
        except Exception as e:
            print(f"Fallo en conexion: {e}")
            resultados.append({"id": item["id"], "pregunta": item["pregunta"], "estado": "ERROR_CONEXION"})

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)
    
    print(f"\nFase completada. Datos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    ejecutar_pruebas()