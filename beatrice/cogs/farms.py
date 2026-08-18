import discord
from discord import app_commands
from discord.ext import commands

from beatrice.checks import channel_cooldown
from beatrice.services import farms as farms_service

NETWORK_EMOJI = {
    "binance-smart-chain": "<:wbanbsc:835977496389877802>",
    "fantom": "<:wbanftm:949720720110419999>",
    "polygon": "<:wbanpoly:884560016928043038>",
    "ethereum": "<:wbaneth:1037739681401536662>",
    "arbitrum": "<:wbanarb:1051565681763688548>",
}


class Farms(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        description="Fetch current TVL and APR for all active wrapped banano farms"
    )
    @app_commands.guild_only()
    @channel_cooldown(1, 300)
    async def farms(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        results = await farms_service.get_wban_farms()
        if results is None:
            await interaction.followup.send("API Error")
            return
        if not results:
            await interaction.followup.send("No active wBAN farms found")
            return
        results.sort(key=lambda item: item[0])

        output = ""
        for network, pools in results:
            emoji = NETWORK_EMOJI.get(network, NETWORK_EMOJI["binance-smart-chain"])
            output += f"\n{emoji} **{str.title(network)}**"
            output += "\n```"
            for pair, tvl, apr in pools:
                if apr is not None:
                    output += f"{pair}: {apr}% APR (${tvl:,} TVL)\n"
                else:
                    output += f"{pair}: Inactive (${tvl:,} TVL)\n"
            output += "```"
        embed = discord.Embed(colour=discord.Colour.green(), title="wBAN Farms", description=output)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Farms(bot))
