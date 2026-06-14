"""
bot.py
Punto de entrada. Inicializa la base de datos y arranca el bot.
"""
import os
import asyncio
import discord
from discord.ext import commands

from core import bd as db

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Conectado como {bot.user}  -  comandos sincronizados")


async def main():
    if not TOKEN:
        raise RuntimeError("Falta la variable de entorno DISCORD_TOKEN")
    db.init_db()
    async with bot:
        await bot.load_extension("cogs.dashboard")
        await bot.load_extension("cogs.simulacion")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
