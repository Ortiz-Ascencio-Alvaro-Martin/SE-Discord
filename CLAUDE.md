# Asesor de Negocios IA — Bot de Discord (Sistema Experto)

Simulador económico de una **cafetería de especialidad en Guadalajara, Jalisco**,
sobre Discord, diseñado como **sistema experto** para la materia (proyecto SE).
El simulador *es* el sistema experto: el dominio de conocimiento es la gestión
económica del negocio. Todos los montos están en **pesos mexicanos (MXN)**.

## Contexto local (Guadalajara / Zona Metropolitana)
La cafetería se ubica en la ZMG. La **zona** elegida afecta la renta y el tráfico
de clientes. Zonas modeladas (multiplicador de renta y de demanda sugeridos,
calibrar con datos reales):

| Zona | Perfil | Renta (mult.) | Demanda (mult.) |
|------|--------|---------------|-----------------|
| Centro Histórico (GDL) | Alto flujo, turismo | 1.0 | 1.1 |
| Col. Americana / Lafayette / Chapultepec | Hub de café de especialidad, público joven | 1.4 | 1.3 |
| Providencia | Comercial, poder adquisitivo alto | 1.5 | 1.2 |
| Andares / Puerta de Hierro (Zapopan) | Premium, plazas | 1.8 | 1.1 |
| Tlaquepaque / Tonalá | Turístico, artesanal | 1.1 | 1.0 |
| Colonia popular / periferia | Renta baja, menos tráfico | 0.6 | 0.8 |

## Arquitectura: 3 agentes (requisito de la rúbrica)
- **Agente 1 — Atención** (`agents.AgenteAtencion`): interpreta el comando/texto
  del usuario y lo convierte en una intención estructurada.
- **Agente 2 — Pedido/Inferencia** (`agents.AgentePedido`): inyecta el evento
  global, corre el motor de reglas (`rules.py`), calcula el ciclo (`simulation.py`)
  y persiste todo en la BD.
- **Agente 3 — Supervisor** (`agents.AgenteSupervisor`): lee `registro_inferencias`
  y explica en lenguaje natural las decisiones tomadas (explicabilidad).

## Estructura
```
asesor_negocios/
├── bot.py              # punto de entrada; carga los cogs
├── database.py         # acceso a datos (sqlite3, sin ORM)
├── schema.sql          # 6 tablas
├── simulation.py       # fórmulas económicas (funciones puras)
├── rules.py            # motor de inferencias IF-THEN
├── events.py           # motor de eventos macroeconómicos
├── agents.py           # los 3 agentes
├── requirements.txt
└── cogs/
    ├── dashboard.py    # /dashboard (Embed con color condicional)
    └── simulacion.py   # /crear_negocio, /ciclo_avanzar, /proveedor + Buttons/Select
```

## Base de datos (SQLite, local)
`usuarios`, `negocios`, `inventario`, `finanzas_registro`, `historial_eventos`,
`registro_inferencias` (esta última es la columna vertebral de la explicabilidad).

## Fórmulas clave (simulation.py)
- Margen de contribución = `precio − costo_variable_unitario`
- Punto de equilibrio = `costos_fijos / (precio − costo_variable)`
- Demanda con elasticidad = `base × (precio_mercado / precio_usuario) ^ 1.5`
- Flujo neto = `ingresos − (costos_fijos + costos_variables)`
- Unidades vendidas = `min(demanda, capacidad, inventario)`

## Parámetros económicos sugeridos (MXN, calibrar a la realidad de GDL)
Costos fijos por ciclo (mensual):
- Renta base ~$18,000 (× multiplicador de zona)
- Barista Jr. ~$8,500/mes · Barista Certificado ~$12,500/mes
- Servicios (CFE comercial + agua + gas) ~$4,500
- Mantenimiento máquina de espresso ~$1,500

Costos variables por taza:
- Grano comercial ~$6 · Grano de especialidad de origen (Chiapas/Veracruz/Nayarit) ~$14
- Leche entera ~$4 · Alternativa vegetal (avena/almendra) ~$9
- Vaso/empaque desechable ~$3
- Merma estimada: 5–10% del insumo del ciclo

Precio de venta de referencia del mercado: ~$55/taza (especialidad en GDL ronda $50–90).

## Cómo correr
```bash
pip install -r requirements.txt
export DISCORD_TOKEN="..."   # Windows: $env:DISCORD_TOKEN="..."
python bot.py
```
Requiere activar el **Message Content Intent** en el Discord Developer Portal.

## TODO — Visión completa del proyecto
Lo que YA está hecho:
- [x] Slash commands con discord.py
- [x] Embeds con color condicional (verde/amarillo/rojo)
- [x] Los 3 agentes (Atención, Pedido, Supervisor)
- [x] Motor de inferencias IF-THEN con registro/explicabilidad
- [x] Motor de eventos globales
- [x] BD SQLite con 6 tablas
- [x] /dashboard con margen de contribución, punto de equilibrio y flujo neto

Lo que FALTA (de la visión original) — pendiente de programar:
- [ ] **Desglose de costos fijos por zona de GDL:** renta variable según zona,
      sueldos diferenciados (Barista Jr. vs Certificado), servicios y
      mantenimiento de la máquina de espresso. Hoy hay un costo fijo plano de $6,000.
- [ ] **Costos variables reales:** grano comercial vs. especialidad con precios
      distintos, leche vs. alternativa vegetal, vasos/empaques y **mermas**.
      Hoy hay un costo variable plano de $18/taza.
- [ ] **Compensar la elasticidad-precio** invirtiendo en "Calidad del Insumo" o
      "Marketing de Marca" (hoy la demanda solo cae por precio alto, sin contrapeso).
- [ ] **Componentes interactivos faltantes:** botones [Vender] y [Pagar Nómina];
      Select Menu de **campañas de marketing**.
- [ ] **Cerrar el flujo de compra del proveedor:** el Select Menu debe descontar
      de la caja y sumar al inventario (hoy solo registra la intención).
- [ ] Comando `/ajustar_precio` que persista el nuevo precio en `negocios`.
- [ ] Sembrar inventario inicial al crear el negocio.
- [ ] (Opcional) Tests con `pytest` para respaldar las fórmulas en la presentación.

## Eventos macroeconómicos (events.py) — aterrizados a México/GDL
- Helada/sequía en zonas productoras (Chiapas, Veracruz, Brasil): sube el precio del grano.
- Tendencia viral en TikTok: sube la demanda de bebidas frías (útil en el calor de GDL, abril–junio).
- Inflación local: sube la renta y los costos fijos.
- Temporada de lluvias (jun–sep): repunta el consumo de bebidas calientes.
- Eventos de ciudad (FIL, festivales, conciertos): pico temporal de tráfico.
- Competencia: abre una cafetería rival en la zona, baja la demanda.

## Notas
- Toda la lógica económica está en funciones puras (fáciles de probar y explicar).
- El prototipo de la interfaz está en Figma: https://gown-kinder-24829009.figma.site/
- Los parámetros en MXN son valores de simulación sugeridos; conviene calibrarlos
  con datos reales locales antes de la presentación.
