# interfaz_web.py
import streamlit as st
import requests
import uuid

# Configuración de la API
API_URL = "http://localhost:5000/chat"

# Configuración visual de la página
st.set_page_config(page_title="Data Marketplace Assistant")
st.title("Asistente de Productos de Datos")
st.markdown("Pregúntame sobre el catálogo de datos disponible.")

# Inicializar el historial de chat en la memoria del navegador

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Ej: '123e4567-e89b-12d3-a456-426614174000'

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []


if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar el historial de mensajes al recargar la pantalla
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["contenido"])

# Capturar el input del usuario en la parte inferior
pregunta_usuario = st.chat_input("Ej: ¿Tenéis algún dataset sobre economía europea?")

if pregunta_usuario:
    # 1. Mostrar la pregunta del usuario en pantalla y guardarla
    with st.chat_message("user"):
        st.markdown(pregunta_usuario)
    st.session_state.mensajes.append({"rol": "user", "contenido": pregunta_usuario})

    # 2. Llamar a la API de Flask
    with st.chat_message("assistant"):
        with st.spinner("Consultando la base de conocimiento y pensando..."):
            try:
                # Empaquetamos en JSON
                payload = {
                    "pregunta": pregunta_usuario,
                    "session_id": st.session_state.session_id
                }
                
                respuesta_api = requests.post(API_URL, json=payload)
                
                if respuesta_api.status_code == 200:
                    datos = respuesta_api.json()
                    texto_bot = datos["respuesta"]
                    fuentes = datos["documentos_usados"]
                    
                    # Mostramos la respuesta de la IA
                    st.markdown(texto_bot)
                    
                    # (Opcional) Mostrar las fuentes en un desplegable
                    with st.expander("Ver documentos de referencia"):
                        st.text(fuentes)
                        
                    # Guardamos en el historial
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": texto_bot})
                else:
                    st.error(f"Error de la API: {respuesta_api.text}")
                    
            except Exception as e:
                st.error(f"Error de conexión con la API Flask: {e}. ¿Está el servidor encendido?")