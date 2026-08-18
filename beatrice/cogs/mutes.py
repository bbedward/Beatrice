import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from beatrice.checks import admin_only
from beatrice.store import mutes as mute_store
from beatrice.store.models import SilenceList, utcnow

logger = logging.getLogger(__name__)

MAX_SWEEP_FETCHES = 50


class Mutes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cursor = 0

    async def cog_load(self) -> None:
        self.enforce.start()

    async def cog_unload(self) -> None:
        self.enforce.cancel()

    @app_commands.command(description="Muzzle a user, optionally for a duration in minutes")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @admin_only()
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration_minutes: app_commands.Range[float, 0.1] | None = None,
    ) -> None:
        role = interaction.guild.get_role(self.bot.settings.muzzled_role_id)
        if role is None:
            await interaction.response.send_message("Configured role not found.", ephemeral=True)
            return
        expiration = None
        if duration_minutes is not None:
            expiration = utcnow() + datetime.timedelta(minutes=duration_minutes)
        if not await mute_store.silence(user.id, interaction.guild.id, expiration):
            await interaction.response.send_message(f"<@{user.id}> is already muzzled")
            return
        await user.add_roles(role)
        if duration_minutes is not None:
            await interaction.response.send_message(
                f"🚔 <@{user.id}> has been muzzled for {duration_minutes:g} minutes"
            )
        else:
            await interaction.response.send_message(
                f"🚔 <@{user.id}> has been muzzled indefinitely"
            )

    @app_commands.command(description="Unmuzzle a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @admin_only()
    async def unmute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        role = interaction.guild.get_role(self.bot.settings.muzzled_role_id)
        if role is not None:
            await user.remove_roles(role)
        if not await mute_store.unsilence(user.id):
            await interaction.response.send_message(f"<@{user.id}> is not muzzled")
            return
        await interaction.response.send_message(f"<@{user.id}> has been unmuzzled")

    @tasks.loop(seconds=60)
    async def enforce(self) -> None:
        try:
            records = await mute_store.all_silenced()
            now = utcnow()
            expired = [r for r in records if r.expiration is not None and now >= r.expiration]
            expired_ids = {r.id for r in expired}
            active = [r for r in records if r.id not in expired_ids]
            for record in expired:
                await self._expire(record)
            await self._sweep(active)
        except Exception:
            logger.exception("mute enforcement tick failed")

    @enforce.before_loop
    async def before_enforce(self) -> None:
        await self.bot.wait_until_ready()

    async def _expire(self, record: SilenceList) -> None:
        guild = self.bot.get_guild(record.server_id)
        if guild is None:
            await mute_store.unsilence(int(record.user_id))
            return
        try:
            member = await self._fetch(guild, int(record.user_id))
            if member is not None:
                role = guild.get_role(self.bot.settings.muzzled_role_id)
                if role is not None:
                    await member.remove_roles(role)
        except discord.HTTPException:
            logger.warning(
                "could not unmute %s in %s, retrying next tick", record.user_id, guild.id
            )
            return
        await mute_store.unsilence(int(record.user_id))
        logger.info("mute expired for user %s", record.user_id)

    async def _sweep(self, active: list[SilenceList]) -> None:
        if not active:
            return
        start = self._cursor % len(active)
        batch = (active[start:] + active[:start])[:MAX_SWEEP_FETCHES]
        self._cursor = (start + len(batch)) % len(active)
        for record in batch:
            await self._reapply(record)

    async def _reapply(self, record: SilenceList) -> None:
        guild = self.bot.get_guild(record.server_id)
        if guild is None:
            return
        member = await self._fetch(guild, int(record.user_id))
        if member is None:
            return
        role = guild.get_role(self.bot.settings.muzzled_role_id)
        if role is None or role in member.roles:
            return
        try:
            await member.add_roles(role)
        except discord.HTTPException:
            logger.warning("could not re-muzzle %s in %s", record.user_id, guild.id)
            return
        logger.info("re-applied muzzle to %s after rejoin", record.user_id)
        log_channel = guild.get_channel(self.bot.settings.kick_log_channel_id)
        if log_channel is not None:
            await log_channel.send(f"Re-applied muzzle to <@{record.user_id}> after rejoin")

    @staticmethod
    async def _fetch(guild: discord.Guild, user_id: int) -> discord.Member | None:
        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            return None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mutes(bot))
