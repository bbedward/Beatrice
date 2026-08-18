import discord
from discord.ext import commands

PURGE_EMOJI = "❌"
PURGE_THRESHOLD = 5


class Reactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.channel_id != self.bot.settings.reaction_purge_channel_id:
            return
        if str(payload.emoji) != PURGE_EMOJI:
            return
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        reaction = next((r for r in message.reactions if str(r.emoji) == PURGE_EMOJI), None)
        if reaction is None or reaction.count < PURGE_THRESHOLD:
            return
        try:
            await message.delete()
        except discord.NotFound:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reactions(bot))
