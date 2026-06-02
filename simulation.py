from dataclasses import dataclass

@dataclass
class ResultadoCiclo:
    unidades_vendidas: int
    ingresos: float
    costos_variables: float
    costos_fijos: float
    flujo_neto: float


def demanda_estimada(demanda_base: float, precio_mercado: float, precio_usuario: float) -> float:
    # Modelo simple de elasticidad: si precio_usuario > precio_mercado, demanda cae.
    ratio = precio_mercado / max(0.01, precio_usuario)
    return demanda_base * (ratio ** 1.5)


def resolver_ciclo(demanda: float, capacidad: float, inventario_tazas: float, precio: float, costo_variable_unit: float, costos_fijos: float) -> ResultadoCiclo:
    unidades = int(min(capacidad, inventario_tazas, demanda))
    ingresos = unidades * precio
    costos_variables = unidades * costo_variable_unit
    costos_fijos = costos_fijos
    flujo_neto = ingresos - (costos_variables + costos_fijos)
    return ResultadoCiclo(unidades_vendidas=unidades, ingresos=ingresos,
                          costos_variables=costos_variables, costos_fijos=costos_fijos,
                          flujo_neto=flujo_neto)
