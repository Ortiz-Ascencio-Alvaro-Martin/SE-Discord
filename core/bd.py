import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "se_discord.db"


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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                negocio_id INTEGER,
                tipo_insumo TEXT,
                tazas_equiv REAL DEFAULT 0,
                UNIQUE(negocio_id, tipo_insumo)
            )
            """
        )
        try:
            cur.execute("ALTER TABLE negocios ADD COLUMN zona TEXT DEFAULT 'centro'")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE negocios ADD COLUMN marketing_bonus REAL DEFAULT 0.0")
        except Exception:
            pass
        conn.commit()


INVENTARIO_INICIAL = [
    ("grano_comercial", 100.0),
    ("leche",           60.0),
]

def crear_negocio(owner_id: int, owner_name: str, nombre: str, zona: str = "centro"):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO negocios (owner_id, owner_name, nombre, caja, precio_taza, ciclo_actual, zona) VALUES (?,?,?,?,?,?,?)",
            (owner_id, owner_name, nombre, 100_000.0, 55.0, 0, zona),
        )
        negocio_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO inventario (negocio_id, tipo_insumo, tazas_equiv) VALUES (?,?,?)",
            [(negocio_id, tipo, tazas) for tipo, tazas in INVENTARIO_INICIAL],
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


def comprar_insumo(negocio_id: int, tipo_insumo: str, tazas_equiv: float, costo: float) -> bool:
    """Descuenta `costo` de la caja y suma `tazas_equiv` al inventario. Retorna False si no hay fondos."""
    with get_connection() as conn:
        negocio = conn.execute(
            "SELECT caja FROM negocios WHERE negocio_id=?", (negocio_id,)
        ).fetchone()
        if negocio is None or negocio["caja"] < costo:
            return False
        conn.execute(
            "UPDATE negocios SET caja = caja - ? WHERE negocio_id=?",
            (costo, negocio_id),
        )
        conn.execute(
            """
            INSERT INTO inventario (negocio_id, tipo_insumo, tazas_equiv)
            VALUES (?, ?, ?)
            ON CONFLICT(negocio_id, tipo_insumo)
            DO UPDATE SET tazas_equiv = tazas_equiv + excluded.tazas_equiv
            """,
            (negocio_id, tipo_insumo, tazas_equiv),
        )
        conn.commit()
        return True


def obtener_inventario_tazas(negocio_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(tazas_equiv), 0) AS total FROM inventario WHERE negocio_id=?",
            (negocio_id,),
        ).fetchone()
        return row["total"] if row else 0.0


def obtener_inventario_detalle(negocio_id: int) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT tipo_insumo, tazas_equiv FROM inventario WHERE negocio_id=?",
            (negocio_id,),
        ).fetchall()
        return {r["tipo_insumo"]: r["tazas_equiv"] for r in rows}


def consumir_inventario(negocio_id: int, tazas_vendidas: float) -> None:
    """Descuenta tazas_vendidas × 1.075 (merma 7.5%) del inventario, proporcionalmente."""
    tazas_a_consumir = tazas_vendidas * 1.075
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT tipo_insumo, tazas_equiv FROM inventario WHERE negocio_id=? AND tazas_equiv > 0",
            (negocio_id,),
        ).fetchall()
        total = sum(r["tazas_equiv"] for r in rows)
        if total <= 0:
            return
        factor = min(1.0, tazas_a_consumir / total)
        for row in rows:
            nuevo = max(0.0, row["tazas_equiv"] * (1.0 - factor))
            conn.execute(
                "UPDATE inventario SET tazas_equiv=? WHERE negocio_id=? AND tipo_insumo=?",
                (nuevo, negocio_id, row["tipo_insumo"]),
            )
        conn.commit()


def borrar_negocio(negocio_id: int) -> None:
    with get_connection() as conn:
        for tabla in ("inventario", "finanzas_registro", "historial_eventos", "registro_inferencias"):
            conn.execute(f"DELETE FROM {tabla} WHERE negocio_id=?", (negocio_id,))
        conn.execute("DELETE FROM negocios WHERE negocio_id=?", (negocio_id,))
        conn.commit()


def obtener_todos_negocios() -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT negocio_id, nombre, owner_name, caja, ciclo_actual, zona FROM negocios ORDER BY caja DESC"
        ).fetchall()


def obtener_negocio_por_id(negocio_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM negocios WHERE negocio_id=?", (negocio_id,)
        ).fetchone()


def obtener_ultimo_ciclo(negocio_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM finanzas_registro WHERE negocio_id=? ORDER BY ciclo DESC LIMIT 1",
            (negocio_id,),
        ).fetchone()


def ajustar_precio(negocio_id: int, nuevo_precio: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE negocios SET precio_taza=? WHERE negocio_id=?",
            (nuevo_precio, negocio_id),
        )
        conn.commit()


def aplicar_campana_marketing(negocio_id: int, bonus: float, costo: float) -> bool:
    """Suma bonus a marketing_bonus y descuenta costo de caja. False si no hay fondos."""
    with get_connection() as conn:
        negocio = conn.execute(
            "SELECT caja FROM negocios WHERE negocio_id=?", (negocio_id,)
        ).fetchone()
        if negocio is None or negocio["caja"] < costo:
            return False
        conn.execute(
            "UPDATE negocios SET caja = caja - ?, marketing_bonus = marketing_bonus + ? WHERE negocio_id=?",
            (costo, bonus, negocio_id),
        )
        conn.commit()
        return True


def decaer_marketing(negocio_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE negocios SET marketing_bonus = marketing_bonus * 0.5 WHERE negocio_id=?",
            (negocio_id,),
        )
        conn.commit()


def vender_tazas(negocio_id: int, ingresos: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE negocios SET caja = caja + ? WHERE negocio_id=?",
            (ingresos, negocio_id),
        )
        conn.commit()


def pagar_nomina(negocio_id: int, monto: float) -> bool:
    with get_connection() as conn:
        negocio = conn.execute(
            "SELECT caja FROM negocios WHERE negocio_id=?", (negocio_id,)
        ).fetchone()
        if negocio is None or negocio["caja"] < monto:
            return False
        conn.execute(
            "UPDATE negocios SET caja = caja - ? WHERE negocio_id=?",
            (monto, negocio_id),
        )
        conn.commit()
        return True
