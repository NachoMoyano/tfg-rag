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
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
        content = resp.json()['choices'][0]['message']['content'].strip()
        return 1 if "1" in content else 0
    except:
        return 0

def procesar_evaluacion():
    if not json.load(open(INPUT_FILE)): return
    
    data = json.load(open(INPUT_FILE, encoding="utf-8"))
    informe_final = []
    
    print("Iniciando evaluacion de calidad (LLM-as-a-Judge)...")
    
    for r in data:
        if r["estado"] != "OK": continue
        
        print(f"Evaluando calidad de respuesta ID {r['id']}...")
        
        # Test 1: Fidelidad
        prompt_fid = f"""Analiza si la Respuesta se basa solo en el Contexto. 
        Contexto: {r['contexto']}
        Respuesta: {r['respuesta']}
        Responde solo con un numero: 1 si es fiel, 0 si inventa datos."""
        fidelidad = llamar_juez(prompt_fid)
        
        # Test 2: Relevancia
        prompt_rel = f"""Analiza si la Respuesta contesta a la Pregunta.
        Pregunta: {r['pregunta']}
        Respuesta: {r['respuesta']}
        Responde solo con un numero: 1 si es relevante, 0 si no."""
        relevancia = llamar_juez(prompt_rel)
        
        informe_final.append({
            "id": r["id"],
            "latencia": r["latencia"],
            "tps": r["tps"],
            "fidelidad": fidelidad,
            "relevancia": relevancia
        })

    # Resumen Estadistico
    latencias = [x["latencia"] for x in informe_final]
    tps_list = [x["tps"] for x in informe_final]
    fid_list = [x["fidelidad"] for x in informe_final]
    rel_list = [x["relevancia"] for x in informe_final]
    
    print("\n" + "="*40)
    print("INFORME FINAL DE LABORATORIO")
    print("="*40)
    print(f"Muestras validas: {len(informe_final)}")
    print(f"Latencia Media:   {statistics.mean(latencias):.2f}s")
    print(f"TPS Medio:        {statistics.mean(tps_list):.2f} tokens/s")
    print(f"Fidelidad Media:  {statistics.mean(fid_list)*100:.1f}%")
    print(f"Relevancia Media: {statistics.mean(rel_list)*100:.1f}%")
    print("="*40)

if __name__ == "__main__":
    procesar_evaluacion()