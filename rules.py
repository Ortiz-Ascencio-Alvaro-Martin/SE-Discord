"""
rules.py
Motor de inferencias (reglas IF-THEN). Cada regla recibe un "contexto" (dict
con el estado del negocio + mercado) y devuelve una lista de Inferencia.
Las reglas NO tocan la BD: solo razonan. El Agente 2 las ejecuta y persiste.
Esto mantiene la logica pura y facil de explicar/probar.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Inferencia:
    regla: str            # nombre legible de la regla disparada
    entrada: str          # valores que la activaron
    resultado: str        # que se decidio
    explicacion: str      # por que (lenguaje natural, para el Supervisor)
    efectos: dict = field(default_factory=dict)   # cambios a aplicar al estado


# Cada regla es una funcion ctx -> Inferencia | None
Regla = Callable[[dict], Inferencia | None]


def r_stock_insuficiente(ctx: dict) -> Inferencia | None:
    if ctx["inventario_tazas"] < ctx["demanda"]:
        faltante = ctx["demanda"] - ctx["inventario_tazas"]
        return Inferencia(
            regla="IF stock < demanda THEN sugerir reabastecimiento",
            entrada=f"stock={ctx['inventario_tazas']:.0f}, demanda={ctx['demanda']:.0f}",
            resultado=f"Faltan ~{faltante:.0f} tazas de insumo",
            explicacion=("La demanda estimada supera el inventario; se pierden "
                         "ventas por desabasto. Se recomienda reabastecer."),
            efectos={"sugerencia": "reabastecer"},
        )
    return None


def r_precio_alto(ctx: dict) -> Inferencia | None:
    if ctx["precio_usuario"] > ctx["precio_mercado"]:
        sobreprecio = (ctx["precio_usuario"] / ctx["precio_mercado"] - 1) * 100
        return Inferencia(
            regla="IF precio > mercado THEN demanda cae exponencialmente",
            entrada=f"precio={ctx['precio_usuario']:.0f}, mercado={ctx['precio_mercado']:.0f}",
            resultado=f"Sobreprecio de {sobreprecio:.0f}% -> menos clientes",
            explicacion=("Cobras por encima del promedio; la elasticidad-precio "
                         "reduce la afluencia salvo que subas calidad o marketing."),
        )
    return None


def r_riesgo_bancarrota(ctx: dict) -> Inferencia | None:
    if ctx["caja"] < ctx["costos_fijos"]:
        return Inferencia(
            regla="IF caja < costos_fijos THEN alerta de bancarrota",
            entrada=f"caja={ctx['caja']:.0f}, costos_fijos={ctx['costos_fijos']:.0f}",
            resultado="ALERTA: riesgo de no cubrir costos fijos",
            explicacion=("La caja no alcanza para los costos fijos del ciclo. "
                         "Reduce gastos o aumenta ventas urgentemente."),
            efectos={"alerta": "bancarrota"},
        )
    return None


def r_grano_especialidad(ctx: dict) -> Inferencia | None:
    if ctx.get("tipo_grano") == "especialidad":
        return Inferencia(
            regla="IF grano = especialidad THEN reputacion +15%",
            entrada="tipo_grano=especialidad",
            resultado="Reputacion sube",
            explicacion=("El grano de especialidad mejora la percepcion de "
                         "calidad y la reputacion de la marca."),
            efectos={"reputacion_mult": 1.15},
        )
    return None


# Orden de evaluacion del motor
REGLAS: list[Regla] = [
    r_precio_alto,
    r_stock_insuficiente,
    r_grano_especialidad,
    r_riesgo_bancarrota,
]


def evaluar(ctx: dict) -> list[Inferencia]:
    """Corre todas las reglas y devuelve las que se dispararon."""
    disparadas = []
    for regla in REGLAS:
        inf = regla(ctx)
        if inf is not None:
            disparadas.append(inf)
    return disparadas
