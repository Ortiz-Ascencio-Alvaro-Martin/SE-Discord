"""
Motor de eventos macroeconomicos globales. Cada ciclo se puede inyectar un
evento aleatorio que modifica multiplicadores del mercado.
"""
import json
import random
from dataclasses import dataclass


@dataclass
class EventoGlobal:
    tipo: str
    descripcion: str
    impacto: dict


CATALOGO = [
    EventoGlobal(
        "clima",
        "Helada en Brasil: el precio internacional del grano sube 25%.",
        {"costo_grano": 1.25},
    ),
    EventoGlobal(
        "tendencia",
        "Tendencia viral en TikTok: la demanda de bebidas sube 40% este mes.",
        {"demanda": 1.40},
    ),
    EventoGlobal(
        "inflacion",
        "Inflacion local: la renta y los costos fijos suben 5%.",
        {"costos_fijos": 1.05},
    ),
    EventoGlobal(
        "competencia",
        "Abrio una cafeteria rival cerca: la demanda baja 15%.",
        {"demanda": 0.85},
    ),
    EventoGlobal(
        "cosecha",
        "Excelente cosecha en Colombia: el grano baja 10%.",
        {"costo_grano": 0.90},
    ),
    EventoGlobal(
        "estable",
        "Mes tranquilo: el mercado se mantiene estable.",
        {},
    ),
]


def generar_evento(rng: random.Random | None = None) -> EventoGlobal:
    """Elige un evento. 'estable' pesa mas para que no todo sea caos."""
    rng = rng or random
    pesos = [1, 1, 1, 1, 1, 3]
    return rng.choices(CATALOGO, weights=pesos, k=1)[0]


def aplicar_impacto(base: dict, evento: EventoGlobal) -> dict:
    """Devuelve una copia del contexto con los multiplicadores aplicados."""
    ctx = dict(base)
    for clave, mult in evento.impacto.items():
        if clave == "costo_grano":
            ctx["costo_variable_unit"] = ctx["costo_variable_unit"] * mult
        elif clave == "demanda":
            ctx["demanda_base"] = ctx["demanda_base"] * mult
        elif clave == "costos_fijos":
            ctx["costos_fijos"] = ctx["costos_fijos"] * mult
    return ctx


def impacto_json(evento: EventoGlobal) -> str:
    return json.dumps(evento.impacto, ensure_ascii=False)
