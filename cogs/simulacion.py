"""
cogs/simulacion.py
Comandos del motor de simulacion + componentes interactivos.
"""
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core import bd as db
from core.agentes import AgentePedido, AgenteSupervisor, ZONAS, calcular_venta_rapida, _NOMINA

agente_pedido = AgentePedido()
agente_supervisor = AgenteSupervisor()


def color_flujo(flujo: float, caja: float) -> discord.Color:
    if caja <= 0:
        return discord.Color.dark_red()
    if flujo < 0:
        return discord.Color.red()
    if flujo == 0:
        return discord.Color.gold()
    return discord.Color.green()


def embed_ciclo(negocio, res) -> discord.Embed:
    rc = res.resultado_ciclo
    emb = discord.Embed(
        title=f"\U0001F4C5 Ciclo {negocio['ciclo_actual'] + 1} — {negocio['nombre']}",
        description=f"\U0001F30D **Evento global:** {res.evento.descripcion}",
        color=color_flujo(rc.flujo_neto, res.caja_final),
    )
    emb.add_field(name="☕ Tazas vendidas", value=f"{rc.unidades_vendidas:,.0f}", inline=True)
    emb.add_field(name="\U0001F4B0 Ingresos", value=f"${rc.ingresos:,.2f}", inline=True)
    emb.add_field(name="\U0001F4B8 Flujo neto", value=f"${rc.flujo_neto:,.2f}", inline=True)
    emb.add_field(name="\U0001F3E6 Caja final", value=f"${res.caja_final:,.2f}", inline=True)
    emb.add_field(name="\U0001F9E0 Reglas disparadas", value=str(len(res.inferencias)), inline=True)
    emb.set_footer(text="Pulsa 'Ver explicacion' para el reporte del Supervisor")
    return emb


# ---------------- Componentes interactivos ----------------

class PanelCiclo(discord.ui.View):
    def __init__(self, negocio_id: int, ciclo: int):
        super().__init__(timeout=180)
        self.negocio_id = negocio_id
        self.ciclo = ciclo

    @discord.ui.button(label="Avanzar ciclo", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def avanzar(self, interaction: discord.Interaction, button: discord.ui.Button):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return
        res = agente_pedido.procesar_ciclo(negocio)
        negocio = db.obtener_negocio(interaction.user.id)
        await interaction.response.send_message(
            embed=embed_ciclo({**dict(negocio), "ciclo_actual": negocio["ciclo_actual"] - 1}, res),
            view=PanelCiclo(negocio["negocio_id"], negocio["ciclo_actual"]),
        )

    @discord.ui.button(label="Ver explicacion", style=discord.ButtonStyle.secondary, emoji="\U0001F9E0")
    async def explicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = agente_supervisor.explicar(self.negocio_id, self.ciclo)
        emb = discord.Embed(title="\U0001F9E0 Reporte del Supervisor",
                            description=texto, color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @discord.ui.button(label="Vender", style=discord.ButtonStyle.success, emoji="☕")
    async def vender(self, interaction: discord.Interaction, button: discord.ui.Button):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return
        inventario = db.obtener_inventario_detalle(negocio["negocio_id"])
        if not inventario or sum(inventario.values()) <= 0:
            await interaction.response.send_message(
                "Sin inventario. Compra insumos con `/proveedor`.", ephemeral=True
            )
            return
        unidades, ingresos = calcular_venta_rapida(negocio, inventario)
        if unidades <= 0:
            await interaction.response.send_message(
                "La demanda estimada es 0 tazas. Revisa tu precio o invierte en marketing.", ephemeral=True
            )
            return
        db.vender_tazas(negocio["negocio_id"], ingresos)
        db.consumir_inventario(negocio["negocio_id"], unidades)
        db.registrar_inferencia(
            negocio["negocio_id"], negocio["ciclo_actual"],
            "atencion", "venta_rapida",
            f"unidades={unidades}",
            f"Venta rapida: {unidades} tazas a ${negocio['precio_taza']:.0f}",
            f"Se vendieron {unidades} tazas generando ${ingresos:,.0f} MXN sin avanzar ciclo.",
        )
        await interaction.response.send_message(
            f"Vendidas **{unidades} tazas** — +**${ingresos:,.0f} MXN** a caja.",
            ephemeral=True,
        )

    @discord.ui.button(label="Pagar Nomina", style=discord.ButtonStyle.danger, emoji="\U0001F4B3")
    async def pagar_nomina(self, interaction: discord.Interaction, button: discord.ui.Button):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return
        monto = _NOMINA
        ok = db.pagar_nomina(negocio["negocio_id"], monto)
        if not ok:
            await interaction.response.send_message(
                f"❌ Caja insuficiente para pagar nomina (${monto:,.0f} MXN).", ephemeral=True
            )
            return
        db.registrar_inferencia(
            negocio["negocio_id"], negocio["ciclo_actual"],
            "atencion", "pago_nomina",
            f"monto={monto:.0f}",
            "Nomina pagada manualmente",
            f"Se pagaron ${monto:,.0f} MXN al personal fuera del ciclo automatico.",
        )
        await interaction.response.send_message(
            f"\U0001F4B3 Nomina pagada: **-${monto:,.0f} MXN** de caja.", ephemeral=True
        )


class MenuProveedor(discord.ui.Select):
    INSUMOS = {
        "grano_comercial":    {"costo": 300.0,  "tazas": 50,  "label": "Grano comercial"},
        "grano_especialidad": {"costo": 700.0,  "tazas": 50,  "label": "Grano de especialidad"},
        "leche":              {"costo": 120.0,  "tazas": 30,  "label": "Leche entera"},
        "vegetal":            {"costo": 270.0,  "tazas": 30,  "label": "Alternativas vegetales"},
    }

    def __init__(self):
        opciones = [
            discord.SelectOption(label="Grano comercial", description="$300 MXN · +50 tazas · calidad media", value="grano_comercial", emoji="\U0001FAD8"),
            discord.SelectOption(label="Grano de especialidad", description="$700 MXN · +50 tazas · Chiapas/Veracruz", value="grano_especialidad", emoji="✨"),
            discord.SelectOption(label="Leche entera", description="$120 MXN · +30 tazas · insumo base", value="leche", emoji="\U0001F95B"),
            discord.SelectOption(label="Alternativas vegetales", description="$270 MXN · +30 tazas · avena/almendra", value="vegetal", emoji="\U0001F33F"),
        ]
        super().__init__(placeholder="Elige el insumo a comprar...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        eleccion = self.values[0]
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return

        info = self.INSUMOS[eleccion]
        ok = db.comprar_insumo(negocio["negocio_id"], eleccion, info["tazas"], info["costo"])

        if not ok:
            await interaction.response.send_message(
                f"❌ Fondos insuficientes. Necesitas **${info['costo']:,.2f}** "
                f"y tu caja tiene **${negocio['caja']:,.2f}**.",
                ephemeral=True,
            )
            return

        db.registrar_inferencia(
            negocio["negocio_id"], negocio["ciclo_actual"],
            "atencion", "compra_insumo",
            f"insumo={eleccion}",
            f"Compra aprobada: {info['label']}",
            f"Se descontaron ${info['costo']:,.2f} de caja y se sumaron {info['tazas']} tazas al inventario.",
        )

        await interaction.response.send_message(
            f"✅ **{info['label']}** comprado.\n"
            f"\U0001F4B8 `-${info['costo']:,.2f}` de caja — \U0001F4E6 `+{info['tazas']}` tazas al inventario.",
            ephemeral=True,
        )


class VistaProveedor(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MenuProveedor())


class MenuMarketing(discord.ui.Select):
    CAMPANAS = {
        "redes":       {"bonus": 0.10, "costo": 3_000.0,  "label": "Redes sociales"},
        "influencer":  {"bonus": 0.20, "costo": 8_000.0,  "label": "Colaboracion con influencer"},
        "descuento":   {"bonus": 0.25, "costo": 1_500.0,  "label": "Descuento de apertura"},
        "cata":        {"bonus": 0.15, "costo": 5_000.0,  "label": "Evento de cata en tienda"},
    }

    def __init__(self):
        opciones = [
            discord.SelectOption(label="Redes sociales", description="+10% demanda · $3,000 MXN · efecto 1 ciclo", value="redes", emoji="\U0001F4F1"),
            discord.SelectOption(label="Colaboracion con influencer", description="+20% demanda · $8,000 MXN", value="influencer", emoji="\U0001F31F"),
            discord.SelectOption(label="Descuento de apertura", description="+25% demanda · $1,500 MXN", value="descuento", emoji="\U0001F3F7️"),
            discord.SelectOption(label="Evento de cata en tienda", description="+15% demanda · $5,000 MXN", value="cata", emoji="☕"),
        ]
        super().__init__(placeholder="Elige una campana de marketing...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        eleccion = self.values[0]
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return
        info = self.CAMPANAS[eleccion]
        ok = db.aplicar_campana_marketing(negocio["negocio_id"], info["bonus"], info["costo"])
        if not ok:
            await interaction.response.send_message(
                f"❌ Fondos insuficientes. Necesitas **${info['costo']:,.0f} MXN**.", ephemeral=True
            )
            return
        db.registrar_inferencia(
            negocio["negocio_id"], negocio["ciclo_actual"],
            "atencion", "campana_marketing",
            f"campana={eleccion}",
            f"Marketing: {info['label']} (+{info['bonus']*100:.0f}% demanda)",
            f"Se invirtieron ${info['costo']:,.0f} MXN en {info['label']}. "
            f"La demanda sube {info['bonus']*100:.0f}% este ciclo (efecto decae 50% cada ciclo).",
        )
        await interaction.response.send_message(
            f"\U0001F4F1 **{info['label']}** activada.\n"
            f"\U0001F4C8 +{info['bonus']*100:.0f}% demanda este ciclo — "
            f"\U0001F4B8 `-${info['costo']:,.0f} MXN` de caja.",
            ephemeral=True,
        )


class VistaMarketing(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MenuMarketing())


# ---------------- Cog ----------------

class Simulacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    _ZONAS_CHOICES = [
        Choice(name="Centro Historico GDL — alto flujo, turismo", value="centro"),
        Choice(name="Col. Americana / Chapultepec — hub de especialidad", value="americana"),
        Choice(name="Providencia — comercial, poder adquisitivo alto", value="providencia"),
        Choice(name="Andares / Puerta de Hierro — premium, plazas", value="andares"),
        Choice(name="Tlaquepaque / Tonala — turistico, artesanal", value="tlaquepaque"),
        Choice(name="Periferia / Colonia popular — renta baja", value="periferia"),
    ]

    @app_commands.command(name="crear_negocio", description="Crea tu cafeteria en GDL")
    @app_commands.describe(nombre="Nombre de tu cafeteria", zona="Zona de la ZMG donde se ubica")
    @app_commands.choices(zona=_ZONAS_CHOICES)
    async def crear_negocio(self, interaction: discord.Interaction, nombre: str, zona: Choice[str]):
        if db.obtener_negocio(interaction.user.id) is not None:
            await interaction.response.send_message("Ya tienes una cafeteria.", ephemeral=True)
            return
        mult = ZONAS[zona.value]
        db.crear_negocio(interaction.user.id, str(interaction.user), nombre, zona.value)
        await interaction.response.send_message(
            f"☕ Cafeteria **{nombre}** creada en **{zona.name}**.\n"
            f"Renta ×{mult['mult_renta']} · Demanda ×{mult['mult_demanda']} · Caja inicial: $100,000 MXN\n"
            f"Usa `/dashboard` para ver tu estado.",
            ephemeral=True,
        )

    @app_commands.command(name="ciclo_avanzar", description="Simula el siguiente ciclo fiscal")
    async def ciclo_avanzar(self, interaction: discord.Interaction):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message(
                "Primero crea tu cafeteria con `/crear_negocio`.", ephemeral=True
            )
            return
        res = agente_pedido.procesar_ciclo(negocio)
        negocio_act = db.obtener_negocio(interaction.user.id)
        await interaction.response.send_message(
            embed=embed_ciclo({**dict(negocio_act),
                               "ciclo_actual": negocio_act["ciclo_actual"] - 1}, res),
            view=PanelCiclo(negocio_act["negocio_id"], negocio_act["ciclo_actual"]),
        )

    @app_commands.command(name="proveedor", description="Compra insumos del proveedor")
    async def proveedor(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "\U0001F69A **Proveedor** — selecciona qué comprar:",
            view=VistaProveedor(), ephemeral=True,
        )

    @app_commands.command(name="marketing", description="Lanza una campana de marketing para tu cafeteria")
    async def marketing(self, interaction: discord.Interaction):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message(
                "Primero crea tu cafeteria con `/crear_negocio`.", ephemeral=True
            )
            return
        bonus_actual = negocio.get("marketing_bonus") or 0.0
        await interaction.response.send_message(
            f"\U0001F4F1 **Marketing** — bonus activo: `+{bonus_actual*100:.0f}%` demanda\n"
            "Elige una campana (el efecto decae 50% cada ciclo):",
            view=VistaMarketing(), ephemeral=True,
        )

    @app_commands.command(name="ajustar_precio", description="Cambia el precio de tu taza de cafe")
    @app_commands.describe(precio="Nuevo precio por taza (debe ser mayor al costo variable: $18)")
    async def ajustar_precio(self, interaction: discord.Interaction, precio: float):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message(
                "Primero crea tu cafeteria con `/crear_negocio`.", ephemeral=True
            )
            return

        COSTO_VARIABLE = 13.0
        PRECIO_MERCADO = 55.0

        if precio < COSTO_VARIABLE:
            await interaction.response.send_message(
                f"❌ El precio minimo es **${COSTO_VARIABLE:.2f}** (costo variable unitario). "
                f"Con ${precio:.2f} operarias con perdida garantizada.",
                ephemeral=True,
            )
            return

        precio_anterior = negocio["precio_taza"]
        db.ajustar_precio(negocio["negocio_id"], precio)

        db.registrar_inferencia(
            negocio["negocio_id"], negocio["ciclo_actual"],
            "atencion", "ajuste_precio",
            f"precio_anterior={precio_anterior:.2f}",
            f"Precio actualizado a ${precio:.2f}",
            f"El usuario cambio el precio de ${precio_anterior:.2f} a ${precio:.2f}. "
            f"Precio de mercado referencia: ${PRECIO_MERCADO:.2f}.",
        )

        diferencia = precio - PRECIO_MERCADO
        if diferencia > 10:
            nota = f"\n⚠️ Tu precio esta **${diferencia:.2f} por encima** del mercado (${PRECIO_MERCADO:.2f}). Podrias perder demanda."
        elif diferencia < -10:
            nota = f"\n⚠️ Tu precio esta **${abs(diferencia):.2f} por debajo** del mercado (${PRECIO_MERCADO:.2f}). Revisa tu margen."
        else:
            nota = ""

        await interaction.response.send_message(
            f"✅ Precio actualizado: **${precio_anterior:.2f} → ${precio:.2f}** por taza.{nota}",
            ephemeral=True,
        )

    @app_commands.command(name="borrar_negocio", description="Elimina tu cafeteria permanentemente")
    async def borrar_negocio(self, interaction: discord.Interaction):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return

        class ConfirmBorrar(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)

            @discord.ui.button(label="Si, borrar", style=discord.ButtonStyle.danger, emoji="🗑️")
            async def confirmar(self, inter: discord.Interaction, button: discord.ui.Button):
                db.borrar_negocio(negocio["negocio_id"])
                self.stop()
                await inter.response.edit_message(
                    content=f"✅ Cafeteria **{negocio['nombre']}** eliminada.", view=None
                )

            @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
            async def cancelar(self, inter: discord.Interaction, button: discord.ui.Button):
                self.stop()
                await inter.response.edit_message(content="Cancelado.", view=None)

        await interaction.response.send_message(
            f"⚠️ ¿Seguro que quieres borrar **{negocio['nombre']}**? Se eliminan todos los datos (inventario, historial, finanzas).",
            view=ConfirmBorrar(), ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Simulacion(bot))
