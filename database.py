import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "se_discord.db"


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS negocios (
                negocio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                owner_name TEXT,
                nombre TEXT,
                caja REAL,
                precio_taza REAL,
                ciclo_actual INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS finanzas_registro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                negocio_id INTEGER,
                ciclo INTEGER,
                ingresos REAL,
                costos_fijos REAL,
                costos_variables REAL,
                flujo_neto REAL,
                caja_final REAL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historial_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                negocio_id INTEGER,
                ciclo INTEGER,
                tipo TEXT,
                descripcion TEXT,
                impacto_json TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS registro_inferencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                negocio_id INTEGER,
                ciclo INTEGER,
                agente TEXT,
                regla TEXT,
                entrada TEXT,
                resultado TEXT,
                explicacion TEXT
            )
            """
        )
        conn.commit()


def crear_negocio(owner_id: int, owner_name: str, nombre: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO negocios (owner_id, owner_name, nombre, caja, precio_taza, ciclo_actual) VALUES (?,?,?,?,?,?)",
            (owner_id, owner_name, nombre, 10000.0, 45.0, 0),
        )
        conn.commit()


def obtener_negocio(owner_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM negocios WHERE owner_id=?",
            (owner_id,),
        ).fetchone()
        return row


def registrar_inferencia(negocio_id: int, ciclo: int, agente: str, regla: str, entrada: str, resultado: str, explicacion: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO registro_inferencias (negocio_id, ciclo, agente, regla, entrada, resultado, explicacion) VALUES (?,?,?,?,?,?,?)",
            (negocio_id, ciclo, agente, regla, entrada, resultado, explicacion),
        )
        conn.commit()
