import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands
from redis.asyncio import Redis

from beatrice.config import Settings
from beatrice.store import migrate

logger = logging.getLogger(__name__)

EXTENSIONS = (
    "beatrice.cogs.gallery",
    "beatrice.cogs.prices",
    "beatrice.cogs.folding",
    "beatrice.cogs.farms",
    "beatrice.cogs.moderation",
    "beatrice.cogs.roles",
    "beatrice.cogs.mutes",
    "beatrice.cogs.reactions",
)


class Beatrice(commands.Bot):
    def __init__(self, settings: Settings, redis: Redis):
        intents = discord.Intents(guilds=True, guild_reactions=True)
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            chunk_guilds_at_startup=False,
            help_command=None,
        )
        self.settings = settings
        self.redis = redis
        self._synced = False
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self) -> None:
        await asyncio.to_thread(migrate.run)
        for extension in EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self) -> None:
        logger.info(
            "Beatrice online as %s (%s), discord.py %s",
            self.user,
            self.user.id,
            discord.__version__,
        )
        if self._synced:
            return
        for guild in self.guilds:
            await self._sync_guild(guild)
        self._synced = True

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._sync_guild(guild)

    async def _sync_guild(self, guild: discord.Guild) -> None:
        self.tree.copy_global_to(guild=guild)
        try:
            await self.tree.sync(guild=guild)
        except discord.Forbidden:
            logger.error(
                "cannot sync commands to guild %s (%s): bot is missing the "
                "applications.commands scope - re-invite it with that scope",
                guild.name,
                guild.id,
            )
            return
        except discord.HTTPException:
            logger.exception("command sync failed for guild %s (%s)", guild.name, guild.id)
            return
        logger.info("synced command tree to guild %s (%s)", guild.name, guild.id)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await self._respond(interaction, f"Slow down — try again in {error.retry_after:.0f}s.")
            return
        if isinstance(error, app_commands.CheckFailure):
            await self._respond(interaction, "You can't use that command here.")
            return
        logger.exception("command %s failed", interaction.command, exc_info=error)
        await self._respond(interaction, "Something went wrong.")

    @staticmethod
    async def _respond(interaction: discord.Interaction, message: str) -> None:
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass
