"""
Los 3 agentes del sistema experto.

  Agente 1 - Atencion:   interpreta la intencion del usuario.
  Agente 2 - Pedido:     valida, infiere (motor de reglas), calcula y persiste.
  Agente 3 - Supervisor: explica las decisiones leyendo el registro de inferencias.
"""
from dataclasses import dataclass

from . import bd as db
from . import economia as sim
from . import reglas as rules
from . import eventos as events


# ---------------- AGENTE 1: ATENCION ----------------

@dataclass
class Intencion:
    accion: str
    parametros: dict


class AgenteAtencion:
    """Traduce texto/comando del usuario a una intencion estructurada."""

    def interpretar(self, texto: str) -> Intencion:
        t = texto.lower().strip()
        if any(p in t for p in ("avanzar", "siguiente", "ciclo", "mes")):
            return Intencion("avanzar_ciclo", {})
        if any(p in t for p in ("comprar", "reabastecer", "pedir")):
            return Intencion("comprar", {"item": "grano"})
        if "precio" in t:
            return Intencion("ajustar_precio", {})
        return Intencion("desconocida", {})


# ---------------- AGENTE 2: PEDIDO / INFERENCIA ----------------

@dataclass
class ResultadoAgentePedido:
    evento: events.EventoGlobal
    resultado_ciclo: sim.ResultadoCiclo
    inferencias: list[rules.Inferencia]
    caja_final: float


ZONAS = {
    "centro":      {"mult_renta": 1.0, "mult_demanda": 1.1},
    "americana":   {"mult_renta": 1.4, "mult_demanda": 1.3},
    "providencia": {"mult_renta": 1.5, "mult_demanda": 1.2},
    "andares":     {"mult_renta": 1.8, "mult_demanda": 1.1},
    "tlaquepaque": {"mult_renta": 1.1, "mult_demanda": 1.0},
    "periferia":   {"mult_renta": 0.6, "mult_demanda": 0.8},
}

_RENTA_BASE = 18_000.0
_NOMINA = 8_500.0
_COSTOS_FIJOS_SIN_RENTA = _NOMINA + 4_500.0 + 1_500.0

_COSTO_GRANO = {"grano_comercial": 6.0, "grano_especialidad": 14.0}
_COSTO_LECHE = {"leche": 4.0, "vegetal": 9.0}
_COSTO_VASO = 3.0
_MERMA = 0.075


def calcular_venta_rapida(negocio: dict, inventario: dict) -> tuple[int, float]:
    """Venta directa sin evento ni costos fijos. Retorna (unidades_vendidas, ingresos)."""
    zona = negocio.get("zona") or "centro"
    mult = ZONAS.get(zona, ZONAS["centro"])
    marketing_bonus = negocio.get("marketing_bonus") or 0.0
    tipo_grano = "especialidad" if inventario.get("grano_especialidad", 0) > 0 else "comercial"
    demanda_base = 500.0 * mult["mult_demanda"]
    if tipo_grano == "especialidad":
        demanda_base *= 1.15
    demanda_base *= (1 + marketing_bonus)
    demanda = sim.demanda_estimada(demanda_base, 55.0, negocio["precio_taza"])
    inventario_tazas = sum(inventario.values())
    unidades = int(min(demanda, 700.0, inventario_tazas))
    return unidades, unidades * negocio["precio_taza"]


def parametros_negocio(negocio: dict, inventario: dict) -> dict:
    """Devuelve costos_fijos y costo_variable_unit para un negocio dado."""
    zona = negocio.get("zona") or "centro"
    mult = ZONAS.get(zona, ZONAS["centro"])
    return {
        "costos_fijos": _RENTA_BASE * mult["mult_renta"] + _COSTOS_FIJOS_SIN_RENTA,
        "costo_variable_unit": _calcular_costo_variable(inventario),
    }


def _calcular_costo_variable(inventario: dict) -> float:
    grain = _COSTO_GRANO["grano_especialidad"] if inventario.get("grano_especialidad", 0) > 0 else _COSTO_GRANO["grano_comercial"]
    leche = _COSTO_LECHE["vegetal"] if (inventario.get("vegetal", 0) > 0 and inventario.get("leche", 0) == 0) else _COSTO_LECHE["leche"]
    return (grain + leche + _COSTO_VASO) * (1 + _MERMA)


class AgentePedido:
    """Procesa el ciclo: inyecta evento, corre reglas, calcula y persiste."""

    def procesar_ciclo(self, negocio, rng=None) -> ResultadoAgentePedido:
        nuevo_ciclo = negocio["ciclo_actual"] + 1

        zona = negocio.get("zona") or "centro"
        mult = ZONAS.get(zona, ZONAS["centro"])
        costos_fijos = _RENTA_BASE * mult["mult_renta"] + _COSTOS_FIJOS_SIN_RENTA

        inventario = db.obtener_inventario_detalle(negocio["negocio_id"])
        inventario_tazas = sum(inventario.values()) or 600.0

        tipo_grano = "especialidad" if inventario.get("grano_especialidad", 0) > 0 else "comercial"
        costo_variable_unit = _calcular_costo_variable(inventario)

        marketing_bonus = negocio.get("marketing_bonus") or 0.0
        demanda_base = 500.0 * mult["mult_demanda"]
        if tipo_grano == "especialidad":
            demanda_base *= 1.15
        demanda_base *= (1 + marketing_bonus)

        ctx = {
            "demanda_base": demanda_base,
            "precio_mercado": 55.0,
            "precio_usuario": negocio["precio_taza"],
            "costo_variable_unit": costo_variable_unit,
            "costos_fijos": costos_fijos,
            "caja": negocio["caja"],
            "inventario_tazas": inventario_tazas,
            "tipo_grano": tipo_grano,
            "capacidad": 700.0,
        }

        evento = events.generar_evento(rng)
        ctx = events.aplicar_impacto(ctx, evento)

        ctx["demanda"] = sim.demanda_estimada(
            ctx["demanda_base"], ctx["precio_mercado"], ctx["precio_usuario"]
        )

        inferencias = rules.evaluar(ctx)

        rc = sim.resolver_ciclo(
            demanda=ctx["demanda"],
            capacidad=ctx["capacidad"],
            inventario_tazas=ctx["inventario_tazas"],
            precio=ctx["precio_usuario"],
            costo_variable_unit=ctx["costo_variable_unit"],
            costos_fijos=ctx["costos_fijos"],
        )
        caja_final = negocio["caja"] + rc.flujo_neto

        nid = negocio["negocio_id"]
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO finanzas_registro "
                "(negocio_id, ciclo, ingresos, costos_fijos, costos_variables, "
                " flujo_neto, caja_final) VALUES (?,?,?,?,?,?,?)",
                (nid, nuevo_ciclo, rc.ingresos, rc.costos_fijos,
                 rc.costos_variables, rc.flujo_neto, caja_final),
            )
            conn.execute(
                "INSERT INTO historial_eventos "
                "(negocio_id, ciclo, tipo, descripcion, impacto_json) "
                "VALUES (?,?,?,?,?)",
                (nid, nuevo_ciclo, evento.tipo, evento.descripcion,
                 events.impacto_json(evento)),
            )
            conn.execute(
                "UPDATE negocios SET caja=?, ciclo_actual=? WHERE negocio_id=?",
                (caja_final, nuevo_ciclo, nid),
            )

        for inf in inferencias:
            db.registrar_inferencia(
                nid, nuevo_ciclo, "pedido", inf.regla,
                inf.entrada, inf.resultado, inf.explicacion,
            )

        db.consumir_inventario(nid, rc.unidades_vendidas)
        db.decaer_marketing(nid)

        return ResultadoAgentePedido(evento, rc, inferencias, caja_final)


# ---------------- AGENTE 3: SUPERVISOR ----------------

class AgenteSupervisor:
    """Explica en lenguaje natural lo que hizo el Agente 2."""

    def explicar(self, negocio_id: int, ciclo: int) -> str:
        with db.get_connection() as conn:
            infs = conn.execute(
                "SELECT regla, resultado, explicacion FROM registro_inferencias "
                "WHERE negocio_id=? AND ciclo=? ORDER BY id",
                (negocio_id, ciclo),
            ).fetchall()

        if not infs:
            return "No se dispararon reglas especiales este ciclo. Operacion normal."

        lineas = ["**Decisiones tomadas por el sistema:**"]
        for i in infs:
            lineas.append(f"• {i['resultado']}\n  ↳ {i['explicacion']}")
        return "\n".join(lineas)
