import discord
from discord import app_commands
from discord.ext import commands

from beatrice.checks import user_cooldown
from beatrice.services import folding


class Folding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="fodl",
        description="Verify Folding@Home Bananominer client configuration",
    )
    @user_cooldown(1, 5)
    async def fodl(self, interaction: discord.Interaction, username: str) -> None:
        if not folding.valid_username(username):
            await interaction.response.send_message(
                "Definitely not a bananominer username.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        username = username.lower()
        try:
            fah, bminer, bonus = await folding.fetch_user_data(username)
            report = folding.build_report(username, fah, bminer, bonus)
        except (KeyError, TypeError):
            report = None
        if report is None:
            await interaction.followup.send("API Error", ephemeral=True)
            return
        embed = discord.Embed(colour=discord.Colour.teal(), title="FODL Check", description=report)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Folding(bot))
