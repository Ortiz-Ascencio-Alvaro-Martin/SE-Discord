import discord
from discord import app_commands
from discord.ext import commands

from core import bd as db
from core.agentes import parametros_negocio

ZONAS_LABELS = {
    "centro":      "Centro Historico GDL",
    "americana":   "Col. Americana / Chapultepec",
    "providencia": "Providencia",
    "andares":     "Andares / Puerta de Hierro",
    "tlaquepaque": "Tlaquepaque / Tonala",
    "periferia":   "Periferia / Colonia popular",
}

INSUMO_LABEL = {
    "grano_comercial":    "Grano comercial",
    "grano_especialidad": "Grano especialidad",
    "leche":              "Leche entera",
    "vegetal":            "Alternativa vegetal",
}


def _color(caja: float, flujo: float | None) -> discord.Color:
    if caja <= 0:
        return discord.Color.dark_red()
    if flujo is None:
        return discord.Color.blurple()
    if flujo >= 0:
        return discord.Color.green()
    if flujo >= -5_000:
        return discord.Color.gold()
    return discord.Color.red()


def build_embed(negocio, inventario: dict, ultimo_ciclo) -> discord.Embed:
    zona_label = ZONAS_LABELS.get(negocio.get("zona") or "centro", "Desconocida")
    flujo = ultimo_ciclo["flujo_neto"] if ultimo_ciclo else None

    params = parametros_negocio(negocio, inventario)
    costo_var = params["costo_variable_unit"]
    costos_fijos = params["costos_fijos"]
    precio = negocio["precio_taza"]
    margen = precio - costo_var
    pe = costos_fijos / margen if margen > 0 else float("inf")
    marketing_bonus = negocio.get("marketing_bonus") or 0.0

    emb = discord.Embed(
        title=negocio["nombre"],
        description=f"{zona_label}  ·  Ciclo #{negocio['ciclo_actual']}  ·  {negocio['owner_name']}",
        color=_color(negocio["caja"], flujo),
    )

    mkt = f"+{marketing_bonus*100:.0f}% demanda" if marketing_bonus > 0.01 else "—"
    emb.add_field(name="Caja", value=f"**${negocio['caja']:,.0f}** MXN", inline=True)
    emb.add_field(name="Precio / taza", value=f"${precio:.0f} MXN", inline=True)
    emb.add_field(name="Marketing activo", value=mkt, inline=True)

    if inventario:
        total_tazas = sum(inventario.values())
        lineas = []
        for tipo, tazas in inventario.items():
            label = INSUMO_LABEL.get(tipo, tipo)
            lineas.append(f"`{label:<22} {tazas:>5.0f} tz`")
        lineas.append(f"`{'Total':<22} {total_tazas:>5.0f} tz`")
        emb.add_field(name="Inventario", value="\n".join(lineas), inline=False)
    else:
        emb.add_field(name="Inventario", value="_Sin insumos — usa_ `/proveedor`", inline=False)

    if ultimo_ciclo:
        uc = ultimo_ciclo
        signo = "+" if uc["flujo_neto"] >= 0 else ""
        emb.add_field(
            name=f"Ultimo ciclo  (#{uc['ciclo']})",
            value=(
                f"`Tazas vendidas   {uc['ingresos'] / precio if precio else 0:>6.0f}`\n"
                f"`Ingresos         ${uc['ingresos']:>9,.0f}`\n"
                f"`Costos fijos     ${uc['costos_fijos']:>9,.0f}`\n"
                f"`Costos variables ${uc['costos_variables']:>9,.0f}`\n"
                f"`Flujo neto      {signo}${uc['flujo_neto']:>9,.0f}`"
            ),
            inline=False,
        )

    pe_str = f"{pe:,.0f} tz/ciclo" if pe != float("inf") else "N/A"
    emb.add_field(
        name="Indicadores",
        value=(
            f"`Margen contribucion  ${margen:>7.2f}/tz`\n"
            f"`Punto de equilibrio  {pe_str:>10}`\n"
            f"`Costo variable unit  ${costo_var:>7.2f}/tz`\n"
            f"`Costos fijos/ciclo   ${costos_fijos:>9,.0f}`"
        ),
        inline=False,
    )

    emb.set_footer(text="/ciclo_avanzar  /proveedor  /marketing  /ajustar_precio  /borrar_negocio")
    return emb


async def _enviar_dashboard(interaction: discord.Interaction, negocio_id: int, followup: bool = False):
    negocio = db.obtener_negocio_por_id(negocio_id)
    inventario = db.obtener_inventario_detalle(negocio_id)
    ultimo_ciclo = db.obtener_ultimo_ciclo(negocio_id)
    emb = build_embed(negocio, inventario, ultimo_ciclo)
    if followup:
        await interaction.followup.send(embed=emb)
    else:
        await interaction.response.send_message(embed=emb)


class MenuNegocios(discord.ui.Select):
    def __init__(self, negocios: list):
        opciones = []
        for n in negocios[:25]:
            zona_label = ZONAS_LABELS.get(n.get("zona") or "centro", "?")
            desc = f"{n['owner_name']} · {zona_label} · Ciclo #{n['ciclo_actual']}"
            opciones.append(discord.SelectOption(
                label=n["nombre"][:25],
                description=desc[:100],
                value=str(n["negocio_id"]),
                emoji="☕",
            ))
        super().__init__(placeholder="Elige un negocio...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await _enviar_dashboard(interaction, int(self.values[0]), followup=True)


class VistaNegocios(discord.ui.View):
    def __init__(self, negocios: list):
        super().__init__(timeout=60)
        self.add_item(MenuNegocios(negocios))


class Dashboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="Muestra el estado completo de una cafeteria")
    async def dashboard(self, interaction: discord.Interaction):
        negocios = db.obtener_todos_negocios()

        if not negocios:
            await interaction.response.send_message(
                "Aun no hay cafeterias. Usa `/crear_negocio` para empezar.", ephemeral=True
            )
            return

        if len(negocios) == 1:
            await _enviar_dashboard(interaction, negocios[0]["negocio_id"])
            return

        await interaction.response.send_message(
            f"☕ Hay **{len(negocios)} cafeterias** — elige cuál ver:",
            view=VistaNegocios(negocios),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Dashboard(bot))
