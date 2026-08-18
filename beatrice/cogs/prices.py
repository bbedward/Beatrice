import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from beatrice.checks import channel_cooldown
from beatrice.services import prices

logger = logging.getLogger(__name__)


class Prices(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._status_unit = "usd"

    async def cog_load(self) -> None:
        self.ticker.start()

    async def cog_unload(self) -> None:
        self.ticker.cancel()

    @tasks.loop(seconds=30)
    async def ticker(self) -> None:
        try:
            status = await prices.get_status(self.bot.redis)
            if status is None:
                await self.bot.change_presence(activity=discord.Game("Error checking prices"))
                return
            if self._status_unit == "usd":
                await self.bot.change_presence(
                    activity=discord.Game(f"{status['satoshi']:.1f} sats")
                )
                self._status_unit = "sats"
            else:
                await self.bot.change_presence(activity=discord.Game(f"${status['usdprice']:.4f}"))
                self._status_unit = "usd"
        except Exception:
            logger.exception("status ticker tick failed")

    @ticker.before_loop
    async def before_ticker(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(description="Display BANANO/NANO price information")
    @app_commands.guild_only()
    @channel_cooldown(1, 300)
    async def price(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await prices.get_all_prices(self.bot.redis, self.bot.settings.ves_price_enabled)
        await interaction.followup.send(embed=self._build_embed(data))

    @staticmethod
    def _build_embed(data: dict[str, dict | None]) -> discord.Embed:
        banano, nano, btc = data["BANANO"], data["NANO"], data["BTC"]
        embed = discord.Embed(colour=discord.Colour.green(), title="Current Prices")
        ban_per_nan = None

        embed.description = "**BANANO**"
        if banano is None:
            embed.description += "\nCurrently Unavailable\n"
        else:
            if banano["change"] < 0:
                embed.colour = discord.Colour.red()
            embed.description += "```"
            embed.description += f"Rank            : #{banano['rank']}\n"
            if nano is not None:
                ban_in_nano = banano["usdprice"] / nano["usdprice"]
                ban_per_nan = 1 / ban_in_nano
                embed.description += f"Price  (NANO)   : {ban_in_nano:.6f} NANO\n"
            embed.description += f"Price  (BTC)    : {banano['satoshi']:.1f} sats\n"
            embed.description += f"Price  (USD)    : ${banano['usdprice']:.6f}\n"
            if "bolivar" in banano:
                embed.description += f"Price  (VES)    : {banano['bolivar']:.2f} Bs.S\n"
            embed.description += f"Volume (24H)    : {banano['volume']:,.2f} BTC\n"
            embed.description += f"Market Cap      : ${int(banano['mcap']):,}\n"
            embed.description += "```"

        embed.description += "\n**NANO**"
        if nano is None:
            embed.description += "\nCurrently Unavailable\n"
        else:
            embed.description += "```"
            embed.description += f"Rank            : #{nano['rank']}\n"
            embed.description += f"Price  (BTC)    : {nano['btcprice']:.8f} BTC\n"
            embed.description += f"Price  (USD)    : ${nano['usdprice']:.2f}\n"
            if "bolivar" in nano:
                embed.description += f"Price  (VES)    : {nano['bolivar']:.2f} Bs.S\n"
            embed.description += f"Volume (24H)    : {nano['volume']:,.2f} BTC\n"
            embed.description += f"Market Cap      : ${int(nano['mcap']):,}\n"
            embed.description += "```"

        if btc is not None and ban_per_nan is not None:
            embed.set_footer(
                text=f"1 BTC = ${btc['usdprice']:,.2f} | 1 NANO = {ban_per_nan:,.2f} BAN "
                "| Market Data Provided by CoinGecko.com"
            )
        elif btc is not None:
            embed.set_footer(
                text=f"1 BTC = ${btc['usdprice']:,.2f} | Market Data Provided by CoinGecko.com"
            )
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Prices(bot))
