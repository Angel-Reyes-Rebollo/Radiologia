# ============================================================
# database.py — Conexión a la base de datos
# ============================================================
# Este archivo tiene UNA sola responsabilidad:
# conectarse a MySQL y devolver la conexión.
#
# Antes, esta lógica estaba dentro de CustomHandler y se
# repetía en cada función. Ahora está en un solo lugar.
# Si cambias la DB, solo editas ESTE archivo.
# ============================================================

import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import pooling

# load_dotenv() lee tu archivo .env y carga las variables
# para que os.getenv() pueda acceder a ellas
load_dotenv()

# ── Connection Pool ──────────────────────────────────────────
# En tu código original se abría una conexión nueva por cada
# request, lo cual es lento. Un "pool" mantiene varias
# conexiones abiertas y las reutiliza — mucho más eficiente.
# pool_size=5 significa que hay 5 conexiones disponibles
# simultáneamente. Para este proyecto es más que suficiente.

connection_pool = pooling.MySQLConnectionPool(
    pool_name="radiologia_pool",
    pool_size=20,
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),  # ← agregar esta línea
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", ""),
    database=os.getenv("DB_NAME", "radiologia_db")
)


def get_db():
    """
    Devuelve una conexión del pool.

    Uso en cualquier ruta de Flask:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT ...")
        cursor.close()
        db.close()  # esto NO cierra la conexión, la devuelve al pool
    """
    return connection_pool.get_connection()
    return connection_pool.get_connection()
