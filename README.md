# TAI — Asesor de Negocios IA (Bot de Discord)

Simulador económico de una **cafetería de especialidad en Guadalajara, Jalisco**, implementado como **sistema experto** sobre Discord para la materia de Sistemas Expertos.

El sistema modela la gestión económica del negocio con tres agentes de IA, un motor de inferencias IF-THEN, eventos macroeconómicos aleatorios y una base de datos SQLite persistente. Todos los montos están en **pesos mexicanos (MXN)**.

---

## Características

- **3 Agentes** especializados: Atención, Pedido/Inferencia y Supervisor
- **Motor de reglas IF-THEN** con explicabilidad (Agente 3 justifica cada decisión)
- **Economía realista** para la ZMG: 6 zonas, costos por tipo de insumo, merma del 7.5 %, elasticidad-precio
- **Eventos macroeconómicos** aleatorios (heladas, TikTok, inflación, competencia, cosecha)
- **Comandos slash** de Discord con Buttons y Select Menus interactivos
- **Dashboard** con margen de contribución, punto de equilibrio y flujo neto en tiempo real
- **Campañas de marketing** con decaimiento exponencial (×0.5 por ciclo)
- **Inventario** con 4 tipos de insumo y consumo proporcional con merma

---

## Arquitectura del sistema

```
Usuario (Discord)
      │
      ▼
Agente 1 — Atención        interpreta la intención del comando
      │
      ▼
Agente 2 — Pedido          inyecta evento global → motor de reglas →
                           calcula ciclo económico → persiste en BD
      │
      ▼
Agente 3 — Supervisor      lee registro_inferencias y explica decisiones
      │
      ▼
Discord Embed              resultado visible para el usuario
```

---

## Requisitos

- Python 3.11+
- Cuenta de Discord + bot con **Message Content Intent** activado
- Token del bot en el [Discord Developer Portal](https://discord.com/developers/applications)

---

## Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/<tu-usuario>/SE-Discord.git
cd SE-Discord

# 2. Crea y activa un entorno virtual (recomendado)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Instala dependencias
pip install -r requirements.txt
```

---

## Configuración

```bash
# Windows (PowerShell)
$env:DISCORD_TOKEN = "tu_token_aqui"

# Linux / macOS
export DISCORD_TOKEN="tu_token_aqui"
```

Activa el **Message Content Intent** en el portal de desarrolladores de Discord:  
`Applications → Tu Bot → Bot → Privileged Gateway Intents → Message Content Intent ✓`

---

## Ejecución

```bash
python bot.py
```

La base de datos `se_discord.db` se crea automáticamente en el directorio raíz al primer arranque.

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `/crear_negocio` | Crea tu cafetería eligiendo zona de la ZMG |
| `/dashboard` | Muestra estado financiero completo (caja, inventario, indicadores) |
| `/ciclo_avanzar` | Simula un mes fiscal con evento aleatorio y motor de reglas |
| `/proveedor` | Compra insumos (grano comercial/especialidad, leche/vegetal) |
| `/marketing` | Lanza campaña de marketing (+10–25 % demanda) |
| `/ajustar_precio` | Cambia el precio por taza |
| `/borrar_negocio` | Elimina tu cafetería con confirmación |

### Botones interactivos (tras `/ciclo_avanzar`)

| Botón | Acción |
|---|---|
| ⏭ Avanzar ciclo | Corre el siguiente mes sin escribir comando |
| 🧠 Ver explicación | Muestra el reporte del Agente Supervisor |
| ☕ Vender | Venta rápida sin avanzar ciclo |
| 💳 Pagar Nómina | Descuenta nómina manualmente de la caja |

---

## Estructura del proyecto

```
SE-Discord/
├── bot.py               # Punto de entrada
├── requirements.txt
├── se_discord.db        # Base de datos SQLite (generada en runtime)
├── core/
│   ├── bd.py            # Acceso a datos (sqlite3, sin ORM)
│   ├── agentes.py       # Los 3 agentes del sistema experto
│   ├── economia.py      # Fórmulas económicas (funciones puras)
│   ├── reglas.py        # Motor IF-THEN con registro de inferencias
│   └── eventos.py       # Motor de eventos macroeconómicos
├── cogs/
│   ├── simulacion.py    # Comandos /crear_negocio, /ciclo_avanzar, etc.
│   └── dashboard.py     # Comando /dashboard
└── docs/
    ├── GG_registro_Proy.pdf   # Documento de entrega
    └── manual.pdf             # Manual de usuario
```

---

## Fórmulas económicas clave

```
Margen de contribución  = precio − costo_variable_unitario
Punto de equilibrio     = costos_fijos / margen_contribución
Demanda con elasticidad = base × (precio_mercado / precio_usuario) ^ 1.5
Unidades vendidas       = min(demanda, capacidad, inventario)
Flujo neto              = ingresos − (costos_fijos + costos_variables)
```

---

## Zonas de Guadalajara modeladas

| Zona | Mult. Renta | Mult. Demanda |
|---|---|---|
| Centro Histórico GDL | 1.0 | 1.1 |
| Col. Americana / Chapultepec | 1.4 | 1.3 |
| Providencia | 1.5 | 1.2 |
| Andares / Puerta de Hierro | 1.8 | 1.1 |
| Tlaquepaque / Tonalá | 1.1 | 1.0 |
| Periferia / Colonia popular | 0.6 | 0.8 |

---

## Reglas de inferencia (Motor IF-THEN)

| Regla | Condición | Consecuente |
|---|---|---|
| Precio alto | precio_usuario > precio_mercado | Demanda cae exponencialmente |
| Stock insuficiente | inventario < demanda | Sugiere reabastecimiento |
| Grano especialidad | tipo_grano = especialidad | Reputación +15 % |
| Riesgo bancarrota | caja < costos_fijos | Alerta crítica |

---

## Tecnologías utilizadas

- [discord.py 2.x](https://discordpy.readthedocs.io/) — Framework del bot
- Python 3.11 — Lenguaje principal
- SQLite3 — Base de datos embebida
- LaTeX / MiKTeX — Documentación técnica

---

## Información académica

| Campo | Valor |
|---|---|
| Institución | CETI Colomos |
| Materia | Sistemas Expertos |
| Profesor | Mauricio Alejandro Cabrera Arellano |
| Alumno | Alvaro Martin Ortiz Ascencio |
| Grupo | 7E |
