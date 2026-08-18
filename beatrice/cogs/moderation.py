import re

import discord
from discord import app_commands
from discord.ext import commands

from beatrice.checks import admin_only, is_admin

ID_PATTERN = re.compile(r"<@!?(\d{15,20})>|(\d{15,20})")


def parse_user_ids(raw: str) -> list[int]:
    ids = [int(mention or bare) for mention, bare in ID_PATTERN.findall(raw)]
    return list(dict.fromkeys(ids))


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        return guild.get_channel(self.bot.settings.kick_log_channel_id)

    async def _alert_if_excessive(
        self, guild: discord.Guild, actor_id: int, counter_key: str, verb: str, threshold: int
    ) -> None:
        channel = self._log_channel(guild)
        if channel is None:
            return
        count = await self.bot.redis.get(counter_key)
        if count is not None and int(count) > threshold:
            await channel.send(
                f"<@{actor_id}> is {verb} people excessively! <@{self.bot.settings.alert_user_id}>"
            )

    async def _record_action(
        self,
        interaction: discord.Interaction,
        acted: list[str],
        reason: str | None,
        counter_key: str,
        verb: str,
        verb_past: str,
        threshold: int,
        ttl: int,
    ) -> None:
        channel = self._log_channel(interaction.guild)
        redis = self.bot.redis
        if channel is not None and len(acted) > threshold:
            await channel.send(
                f"<@{interaction.user.id}> is {verb} people excessively! "
                f"<@{self.bot.settings.alert_user_id}>"
            )
        count = await redis.get(counter_key)
        total = len(acted) + (int(count) if count is not None else 0)
        await redis.set(counter_key, str(total), ex=ttl)
        if channel is not None:
            mentions = " ".join(acted)
            await channel.send(
                f"<@{interaction.user.id}> {verb_past} {len(acted)} users: {mentions} "
                f"reason: {reason if reason else 'Not Specified'}"
            )

    @app_commands.command(description="Kick a user, optionally more by ID or mention")
    @app_commands.guild_only()
    @admin_only()
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str | None = None,
        more: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        counter_key = f"kickcount_{interaction.user.id}"
        await self._alert_if_excessive(guild, interaction.user.id, counter_key, "kicking", 15)

        targets = [user]
        for user_id in parse_user_ids(more or ""):
            if user_id == user.id:
                continue
            try:
                targets.append(await guild.fetch_member(user_id))
            except discord.NotFound:
                continue

        kicked = []
        for member in targets:
            if is_admin(self.bot.settings, member):
                continue
            try:
                await guild.kick(member, reason=reason)
            except discord.HTTPException:
                continue
            kicked.append(member.mention)
        if not kicked:
            await interaction.followup.send(
                f"No users to kick, {len(targets)} users are ineligible", ephemeral=True
            )
            return

        await self._record_action(
            interaction, kicked, reason, counter_key, "kicking", "KICKED", 15, 600
        )
        await interaction.followup.send(f"Kicked {len(kicked)} users", ephemeral=True)

    @app_commands.command(description="Ban a user, optionally more by ID or mention")
    @app_commands.guild_only()
    @admin_only()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str | None = None,
        more: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        counter_key = f"bancount_{interaction.user.id}"
        await self._alert_if_excessive(guild, interaction.user.id, counter_key, "banning", 10)

        target_ids = [user.id] + [uid for uid in parse_user_ids(more or "") if uid != user.id]
        banned = []
        skipped = 0
        for user_id in target_ids:
            # Departed users have no roles to check, so the explicit admin ID
            # list must be honored even when the member fetch fails.
            if user_id in self.bot.settings.admin_user_ids:
                skipped += 1
                continue
            member = None
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                pass
            if member is not None and is_admin(self.bot.settings, member):
                skipped += 1
                continue
            try:
                await guild.ban(discord.Object(id=user_id), reason=reason, delete_message_seconds=0)
            except discord.HTTPException:
                skipped += 1
                continue
            banned.append(f"<@{user_id}>")
        if not banned:
            await interaction.followup.send(
                f"No users to ban, {skipped} users are ineligible", ephemeral=True
            )
            return

        await self._record_action(
            interaction, banned, reason, counter_key, "banning", "BANNED", 10, 300
        )
        await interaction.followup.send(f"Banned {len(banned)} users", ephemeral=True)

    @app_commands.command(description="Extract user IDs from mentions or raw text")
    async def ids(self, interaction: discord.Interaction, users: str) -> None:
        ids = parse_user_ids(users)
        if not ids:
            await interaction.response.send_message("No user IDs found", ephemeral=True)
            return
        await interaction.response.send_message(
            " ".join(str(user_id) for user_id in ids), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
