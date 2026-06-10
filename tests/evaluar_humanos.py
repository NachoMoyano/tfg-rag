import os
import glob
import json
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS_GLOB = os.path.join(BASE_DIR, "resultados_*.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "resultados_humanos.json")

def detectar_modelos():
    """Busca y carga todos los archivos de resultados_*.json"""
    archivos = glob.glob(RESULTADOS_GLOB)
    modelos = {}
    for ruta in archivos:
        nombre_archivo = os.path.basename(ruta)
        nombre_modelo = nombre_archivo.replace("resultados_", "").replace(".json", "")
        
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            modelos[nombre_modelo] = data
    return modelos

def agrupar_por_pregunta(modelos):
    """Agrupa las respuestas de los diferentes modelos por ID de pregunta"""
    agrupado = {}
    for nombre_modelo, respuestas in modelos.items():
        for r in respuestas:
            # Solo cogemos respuestas que se generaron correctamente
            if r.get("estado") != "OK":
                continue
            
            qid = r["id"]
            if qid not in agrupado:
                agrupado[qid] = {
                    "pregunta": r["pregunta"],
                    "contexto": r.get("contexto", ""),
                    "respuestas": {}
                }
            agrupado[qid]["respuestas"][nombre_modelo] = r["respuesta"]
    return agrupado

def cargar_progreso():
    """Carga evaluaciones previas para poder pausar y reanudar"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_progreso(evaluaciones):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(evaluaciones, f, ensure_ascii=False, indent=4)

def mostrar_resumen(evaluaciones):
    votos = {}
    empates = 0
    for eval_data in evaluaciones.values():
        ganador = eval_data["ganador"]
        if ganador == "EMPATE":
            empates += 1
        else:
            votos[ganador] = votos.get(ganador, 0) + 1
            
    print("\n" + "="*40)
    print("RESUMEN DE EVALUACIÓN HUMANA (A CIEGAS)")
    print("="*40)
    print(f"Total evaluadas: {len(evaluaciones)}")
    print(f"Empates/Ninguna: {empates}")
    
    for modelo, recuento in sorted(votos.items(), key=lambda x: x[1], reverse=True):
        print(f"  > {modelo}: {recuento} votos")
    print("="*40)

def main():
    print("==================================================")
    print("       EVALUACIÓN A CIEGAS DE LLMs (A/B Test)     ")
    print("==================================================")
    
    modelos = detectar_modelos()
    if not modelos:
        print(f"No se han encontrado archivos resultados_*.json en el directorio base.")
        print("Asegúrate de ejecutar primero tests/benchmark_rendimiento.py con varios modelos.")
        return
        
    print(f"Modelos detectados para la prueba: {', '.join(modelos.keys())}")
    
    preguntas_agrupadas = agrupar_por_pregunta(modelos)
    evaluaciones = cargar_progreso()
    
    # QIDs pendientes, ordenados numéricamente
    preguntas_pendientes = sorted([qid for qid in preguntas_agrupadas.keys() if str(qid) not in evaluaciones])
    
    if not preguntas_pendientes:
        print("\n¡Todas las preguntas ya han sido evaluadas!")
        mostrar_resumen(evaluaciones)
        return
        
    print(f"Preguntas por evaluar: {len(preguntas_pendientes)}")
    print("Para salir y guardar el progreso en cualquier momento, presiona 'q'.\n")
    
    for qid in preguntas_pendientes:
        datos = preguntas_agrupadas[qid]
        respuestas = datos["respuestas"]
        
        # Necesitamos al menos 2 modelos para comparar a ciegas
        if len(respuestas) < 2:
            print(f"Saltando pregunta ID {qid} porque hay menos de 2 modelos con respuestas válidas.")
            continue
            
        print("\n" + "═"*80)
        print(f"PREGUNTA ID: {qid}")
        print(f"Usuario: {datos['pregunta']}")
        print("═"*80)
        
        # Barajar modelos aleatoriamente para ocultar la identidad
        nombres_modelos = list(respuestas.keys())
        random.shuffle(nombres_modelos)
        
        for i, nombre in enumerate(nombres_modelos):
            print(f"\n▼ ▼ ▼ OPCIÓN {i+1} ▼ ▼ ▼")
            print(respuestas[nombre])
            print("▲"*20)
            
        print("\n" + "-"*80)
        while True:
            opciones_validas = [str(x) for x in range(1, len(nombres_modelos) + 1)] + ['e', 'q', 'c']
            print(f"¿Cuál es la mejor respuesta? [1-{len(nombres_modelos)}]")
            print(f"[E]mpate/Ninguna | [C]ontexto original | [Q]uardar y Salir")
            
            voto = input("\nTu elección: ").strip().lower()
            
            if voto == 'q':
                print("\nProgreso guardado. Puedes reanudar ejecutando el script de nuevo.")
                mostrar_resumen(evaluaciones)
                return
            elif voto == 'c':
                print("\n" + "░"*80)
                print("CONTEXTO RECUPERADO (Ground Truth aproximado):")
                print(datos['contexto'][:1500] + ("..." if len(datos['contexto']) > 1500 else ""))
                print("░"*80)
                continue
            elif voto == 'e':
                evaluaciones[str(qid)] = {
                    "ganador": "EMPATE", 
                    "opciones_mostradas": nombres_modelos
                }
                print(">> Registrado como empate.")
                break
            elif voto in opciones_validas:
                indice_ganador = int(voto) - 1
                modelo_ganador = nombres_modelos[indice_ganador]
                evaluaciones[str(qid)] = {
                    "ganador": modelo_ganador, 
                    "opciones_mostradas": nombres_modelos
                }
                # Revelamos a quién ha votado para dar feedback inmediato
                print(f">> ¡Votaste por la Opción {voto}! Esa era la respuesta generada por: {modelo_ganador.upper()}")
                break
            else:
                print("Entrada no válida. Inténtalo de nuevo.")
                
        # Guardar después de cada voto para evitar pérdidas de progreso
        guardar_progreso(evaluaciones)
        
    print("\n¡Enhorabuena! Has terminado de evaluar todas las preguntas.")
    mostrar_resumen(evaluaciones)

if __name__ == "__main__":
    main()
