import sqlite3
import os
import time

# Asumimos que el script se ejecuta desde la raíz del proyecto
DB_SQL = os.path.join(os.getcwd(), "Data", "database", "operacion.db")

def leer_logs(limite=5):
    print("\n" + "="*50)
    print(" ÚLTIMOS LOGS DEL SISTEMA")
    print("="*50)
    try:
        conn = sqlite3.connect(DB_SQL)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, nivel, mensaje FROM logs_sistema ORDER BY id DESC LIMIT ?", (limite,))
        filas = cursor.fetchall()
        
        if not filas:
            print("No hay logs registrados todavía.")
            
        for f in reversed(filas):
            print(f"[{f[0]}] {f[1]}: {f[2]}")
        conn.close()
    except Exception as e:
        print(f"Error accediendo a la tabla logs_sistema: {e}")

def leer_historial(limite=5):
    print("\n" + "="*50)
    print(" ÚLTIMOS MENSAJES DE CHAT")
    print("="*50)
    try:
        conn = sqlite3.connect(DB_SQL)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, session_id, rol, contenido FROM historial_chat ORDER BY id DESC LIMIT ?", (limite,))
        filas = cursor.fetchall()
        
        if not filas:
            print("No hay mensajes en el historial todavía.")
            
        for f in reversed(filas):
            # Recortar el contenido si es muy largo para no inundar la terminal
            contenido = f[3]
            if len(contenido) > 80:
                contenido = contenido[:77] + "..."
                
            print(f"[{f[0]}] {f[1]} | {f[2].upper()}: {contenido}")
        conn.close()
    except Exception as e:
        print(f"Error accediendo a la tabla historial_chat: {e}")

if __name__ == "__main__":
    if not os.path.exists(DB_SQL):
        print(f"ERROR: No se encuentra la base de datos en la ruta:\n{DB_SQL}")
    else:
        # Imprime los ultimos 10 registros de cada tabla
        leer_logs(10)
        leer_historial(10)
        print("\nLectura finalizada.\n")