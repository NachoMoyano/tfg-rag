"""
api_orquestador.py — API REST principal (orquestador).

Actúa como punto de entrada del sistema: recibe peticiones HTTP de la interfaz,
coordina los módulos especializados (db, router, retriever) y delega en el
servidor LLM local la generación de la respuesta final.

Endpoint expuesto:
  POST /chat
    Body : { "pregunta": str, "session_id": str }
    Response: { "respuesta": str, "documentos_usados": str, "contexto_recuperado": str }
"""
from flask import Flask, request, jsonify
import requests

from config import LM_STUDIO_URL
import db
import router
import retriever

app = Flask(__name__)

# Garantiza que las tablas SQLite existen antes del primer request
db.init_sqlite()


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    datos = request.json
    pregunta_usuario = datos.get("pregunta", "")
    session_id = datos.get("session_id", "anonimo")

    if not pregunta_usuario:
        return jsonify({"error": "Pregunta vacía"}), 400

    # 1. Recuperar historial previo (antes del enrutador, para tenerlo disponible)
    historial_previo = db.obtener_historial(session_id)

    # 2. Clasificar la intención del usuario
    categoria = router.clasificar(pregunta_usuario)
    db.guardar_log("INFO", f"Enrutador decidió: {categoria}")
    print(f"El enrutador ha decidido buscar en: {categoria}", flush=True)

    # 3. Recuperar contexto relevante de ChromaDB
    resultado = retriever.recuperar_contexto(pregunta_usuario, categoria)
    contexto_texto   = resultado["contexto_texto"]
    fuentes_visuales = resultado["fuentes_visuales"]
    prompt_sistema   = resultado["prompt_sistema"]

    # 4. Construir el prompt aumentado (sistema + historial + contexto + pregunta)
    mensaje_aumentado = (
        f"CONTEXTO RECUPERADO:\n{contexto_texto}\n\n"
        f"PREGUNTA DEL USUARIO:\n{pregunta_usuario}"
    )
    mensajes_llm = [{"role": "system", "content": prompt_sistema}]
    mensajes_llm.extend(historial_previo)
    mensajes_llm.append({"role": "user", "content": mensaje_aumentado})

    # 5. Generar respuesta con el LLM local (segunda invocación al LLM)
    payload = {
        "messages":    mensajes_llm,
        "temperature": 0.3,
        "max_tokens":  1500,
    }

    try:
        respuesta_lm = requests.post(LM_STUDIO_URL, json=payload)
        respuesta_lm.raise_for_status()
        texto_generado = respuesta_lm.json()["choices"][0]["message"]["content"]

        # 6. Persistir el intercambio en SQLite
        db.guardar_mensaje(session_id, "user",      pregunta_usuario)
        db.guardar_mensaje(session_id, "assistant", texto_generado)

        return jsonify({
            "respuesta":           texto_generado,
            "documentos_usados":   fuentes_visuales,
            "contexto_recuperado": contexto_texto,
        })

    except Exception as e:
        db.guardar_log("ERROR", f"Fallo al conectar con LLM: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    # use_reloader=False evita que Werkzeug reinicie el servidor al detectar cambios
    # en ficheros del .venv, lo que causaría recargas del modelo y pérdida de peticiones.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
