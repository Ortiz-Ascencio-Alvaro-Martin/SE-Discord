import discord
from discord import app_commands
from discord.ext import commands

import database as db


class Dashboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="Muestra tu cafeteria")
    async def dashboard(self, interaction: discord.Interaction):
        negocio = db.obtener_negocio(interaction.user.id)
        if negocio is None:
            await interaction.response.send_message("No tienes cafeteria.", ephemeral=True)
            return
        emb = discord.Embed(title=f"Dashboard — {negocio['nombre']}")
        emb.add_field(name="Caja", value=f"${negocio['caja']:.2f}")
        emb.add_field(name="Ciclo", value=str(negocio['ciclo_actual']))
        await interaction.response.send_message(embed=emb, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Dashboard(bot))
