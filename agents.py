"""
agents.py
Los 3 agentes del sistema experto (requisito de la rubrica).

  Agente 1 - Atencion:   interpreta la intencion del usuario.
  Agente 2 - Pedido:     valida, infiere (motor de reglas), calcula y persiste.
  Agente 3 - Supervisor: explica las decisiones leyendo el registro de inferencias.

Todos comparten una BD comun y dejan rastro en `registro_inferencias`.
"""
from dataclasses import dataclass

import database as db
import simulation as sim
import rules
import events


# ---------------- AGENTE 1: ATENCION ----------------

@dataclass
class Intencion:
    accion: str            # 'avanzar_ciclo' | 'comprar' | 'ajustar_precio' | 'desconocida'
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


class AgentePedido:
    """Procesa el ciclo: inyecta evento, corre reglas, calcula y persiste."""

    def procesar_ciclo(self, negocio, rng=None) -> ResultadoAgentePedido:
        nuevo_ciclo = negocio["ciclo_actual"] + 1

        # Contexto base del mercado
        ctx = {
            "demanda_base": 500.0,
            "precio_mercado": 45.0,
            "precio_usuario": negocio["precio_taza"],
            "costo_variable_unit": 18.0,
            "costos_fijos": 6000.0,
            "caja": negocio["caja"],
            "inventario_tazas": 600.0,
            "tipo_grano": "comercial",
            "capacidad": 700.0,
        }

        # 1) Evento global del ciclo
        evento = events.generar_evento(rng)
        ctx = events.aplicar_impacto(ctx, evento)

        # 2) Demanda con elasticidad
        ctx["demanda"] = sim.demanda_estimada(
            ctx["demanda_base"], ctx["precio_mercado"], ctx["precio_usuario"]
        )

        # 3) Motor de inferencias (reglas IF-THEN)
        inferencias = rules.evaluar(ctx)

        # 4) Resolucion economica del ciclo
        rc = sim.resolver_ciclo(
            demanda=ctx["demanda"],
            capacidad=ctx["capacidad"],
            inventario_tazas=ctx["inventario_tazas"],
            precio=ctx["precio_usuario"],
            costo_variable_unit=ctx["costo_variable_unit"],
            costos_fijos=ctx["costos_fijos"],
        )
        caja_final = negocio["caja"] + rc.flujo_neto

        # 5) Persistir todo
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
            lineas.append(f"\u2022 {i['resultado']}\n  \u21B3 {i['explicacion']}")
        return "\n".join(lineas)
