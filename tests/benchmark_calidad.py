import requests
import json
import statistics

# Configuracion
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
INPUT_FILE = "resultados_laboratorio.json"

def llamar_juez(prompt):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 5
    }
    try:
        # Timeout largo porque el juez a veces tarda en procesar el contexto grande
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].strip()
        # Buscamos el 1 o el 0 de forma más segura
        if "1" in content: return 1
        return 0
    except Exception as e:
        print(f"Error en el juez: {e}")
        return 0

def procesar_evaluacion():
    # Abrimos el archivo una sola vez con la codificacion correcta
    try:
        with open(INPUT_FILE, 'r', encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {INPUT_FILE}")
        return
    except UnicodeDecodeError as e:
        print(f"Error de codificación: {e}. Asegúrate de que el JSON sea UTF-8.")
        return

    if not data:
        print("El archivo JSON está vacío.")
        return
    
    informe_final = []
    
    print("Iniciando evaluación de calidad (LLM-as-a-Judge)...")
    
    for r in data:
        # Solo evaluamos si el benchmark de rendimiento terminó bien
        if r.get("estado") != "OK": 
            continue
        
        print(f"Evaluando calidad de respuesta ID {r['id']}...")
        
        # Test 1: Fidelidad (Faithfulness)
        prompt_fid = f"""Analiza si la Respuesta se basa solo en el Contexto. 
        Contexto: {r.get('contexto', '')}
        Respuesta: {r.get('respuesta', '')}
        Responde solo con un numero: 1 si es fiel, 0 si inventa datos o usa info fuera del contexto."""
        
        fidelidad = llamar_juez(prompt_fid)
        
        # Test 2: Relevancia (Relevance)
        prompt_rel = f"""Analiza si la Respuesta contesta directamente a la Pregunta del usuario.
        Pregunta: {r.get('pregunta', '')}
        Respuesta: {r.get('respuesta', '')}
        Responde solo con un numero: 1 si es relevante y util, 0 si no contesta lo pedido."""
        
        relevancia = llamar_juez(prompt_rel)
        
        informe_final.append({
            "id": r["id"],
            "latencia": r["latencia"],
            "tps": r["tps"],
            "fidelidad": fidelidad,
            "relevancia": relevancia
        })

    if not informe_final:
        print("No hay muestras válidas para evaluar.")
        return

    # Resumen Estadístico
    latencias = [x["latencia"] for x in informe_final]
    tps_list = [x["tps"] for x in informe_final]
    fid_list = [x["fidelidad"] for x in informe_final]
    rel_list = [x["relevancia"] for x in informe_final]
    
    print("\n" + "="*40)
    print("INFORME FINAL DE LABORATORIO")
    print("="*40)
    print(f"Muestras válidas: {len(informe_final)}")
    print(f"Latencia Media:   {statistics.mean(latencias):.2f}s")
    print(f"TPS Medio:        {statistics.mean(tps_list):.2f} tokens/s")
    print(f"Fidelidad Media:  {statistics.mean(fid_list)*100:.1f}%")
    print(f"Relevancia Media: {statistics.mean(rel_list)*100:.1f}%")
    print("="*40)
    
    # Opcional: Guardar el informe de calidad para la memoria
    with open("informe_calidad_final.json", "w", encoding="utf-8") as f:
        json.dump(informe_final, f, indent=4, ensure_ascii=False)
    print("Informe detallado guardado en 'informe_calidad_final.json'")

if __name__ == "__main__":
    procesar_evaluacion()