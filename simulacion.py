"""
cogs/simulacion.py
Comandos del motor de simulacion + componentes interactivos:
  /ciclo_avanzar  -> corre un ciclo (Agente 2) y explica (Agente 3)
  /crear_negocio  -> alta de cafeteria
  Botones [Avanzar ciclo] [Ver explicacion]
  Select Menu de proveedor (compra de insumos)
"""
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from agents import AgentePedido, AgenteSupervisor

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
        title=f"\U0001F4C5 Ciclo {negocio['ciclo_actual'] + 1} \u2014 {negocio['nombre']}",
        description=f"\U0001F30D **Evento global:** {res.evento.descripcion}",
        color=color_flujo(rc.flujo_neto, res.caja_final),
    )
    emb.add_field(name="\u2615 Tazas vendidas", value=f"{rc.unidades_vendidas:,.0f}", inline=True)
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

    @discord.ui.button(label="Avanzar ciclo", style=discord.ButtonStyle.primary, emoji="\u23ED\uFE0F")
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


class MenuProveedor(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(label="Grano comercial", description="Barato, calidad media", value="grano_comercial", emoji="\U0001FAD8"),
            discord.SelectOption(label="Grano de especialidad", description="Caro, sube reputacion", value="grano_especialidad", emoji="\u2728"),
            discord.SelectOption(label="Leche entera", description="Insumo base", value="leche", emoji="\U0001F95B"),
            discord.SelectOption(label="Alternativas vegetales", description="Avena/almendra", value="vegetal", emoji="\U0001F33F"),
        ]
        super().__init__(placeholder="Elige el insumo a comprar...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        eleccion = self.values[0]
        await interaction.response.send_message(
            f"Pedido registrado: **{eleccion}**. (Se descontara de la caja al confirmar.)",
            ephemeral=True,
        )


class VistaProveedor(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MenuProveedor())


# ---------------- Cog ----------------

class Simulacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="crear_negocio", description="Crea tu cafeteria")
    @app_commands.describe(nombre="Nombre de tu cafeteria")
    async def crear_negocio(self, interaction: discord.Interaction, nombre: str):
        if db.obtener_negocio(interaction.user.id) is not None:
            await interaction.response.send_message("Ya tienes una cafeteria.", ephemeral=True)
            return
        db.crear_negocio(interaction.user.id, str(interaction.user), nombre)
        await interaction.response.send_message(
            f"\u2615 Cafeteria **{nombre}** creada. Usa `/dashboard` para verla.", ephemeral=True
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
            "\U0001F69A **Proveedor** \u2014 selecciona qué comprar:",
            view=VistaProveedor(), ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Simulacion(bot))
