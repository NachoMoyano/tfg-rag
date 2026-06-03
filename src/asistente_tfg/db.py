"""
db.py — Capa de persistencia relacional (SQLite).

Centraliza todas las operaciones de lectura y escritura sobre la base de datos
de operación: historial de conversación y registro de logs del sistema.
Ningún otro módulo accede directamente a SQLite; toda interacción pasa por aquí.
"""
import sqlite3
from config import DB_SQL


def init_sqlite() -> None:
    """
    Crea las tablas necesarias si no existen.
    Se invoca una sola vez al arrancar el servidor.
    """
    conn = sqlite3.connect(DB_SQL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_chat (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            rol        TEXT,
            contenido  TEXT,
            timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nivel     TEXT,
            mensaje   TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def guardar_mensaje(session_id: str, rol: str, contenido: str) -> None:
    """Inserta un turno de conversación (user o assistant) en el historial."""
    conn = sqlite3.connect(DB_SQL)
    conn.execute(
        "INSERT INTO historial_chat (session_id, rol, contenido) VALUES (?, ?, ?)",
        (session_id, rol, contenido),
    )
    conn.commit()
    conn.close()


def obtener_historial(session_id: str, limite: int = 4) -> list:
    """
    Devuelve los últimos `limite` mensajes de la sesión ordenados de más
    antiguo a más reciente, en el formato de lista de mensajes que espera el LLM.
    """
    conn = sqlite3.connect(DB_SQL)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rol, contenido FROM historial_chat "
        "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limite),
    )
    filas = cursor.fetchall()
    conn.close()
    return [{"role": fila[0], "content": fila[1]} for fila in reversed(filas)]


def guardar_log(nivel: str, mensaje: str) -> None:
    """Registra un evento interno del sistema (INFO, WARNING, ERROR)."""
    conn = sqlite3.connect(DB_SQL)
    conn.execute(
        "INSERT INTO logs_sistema (nivel, mensaje) VALUES (?, ?)",
        (nivel, mensaje),
    )
    conn.commit()
    conn.close()
