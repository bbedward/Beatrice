from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from beatrice.checks import admin_only, channel_cooldown, outside_no_spam_channels
from beatrice.store import images
from beatrice.ui.paginator import send_paginated

Kind = Literal["meme", "pup", "meow", "fridge"]

KIND_META = {
    "meme": ("Meme", discord.Colour.green()),
    "pup": ("Pup", discord.Colour.blue()),
    "meow": ("Meow", discord.Colour.orange()),
    "fridge": ("Fridge", discord.Colour.orange()),
}


class Gallery(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show(self, interaction: discord.Interaction, kind: Kind) -> None:
        label, colour = KIND_META[kind]
        entry = await images.next_entry(kind)
        if entry is None:
            await interaction.response.send_message(
                f"There are no {kind}s! Add some with /gallery add", ephemeral=True
            )
            return
        embed = discord.Embed(colour=colour, title=f"{label} #{entry.id} - {entry.title}")
        embed.set_author(name=entry.author)
        embed.set_image(url=entry.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Display next meme in sequence")
    @app_commands.guild_only()
    @outside_no_spam_channels()
    @channel_cooldown(1, 300)
    async def meme(self, interaction: discord.Interaction) -> None:
        await self._show(interaction, "meme")

    @app_commands.command(description="Display next pup in sequence")
    @app_commands.guild_only()
    @outside_no_spam_channels()
    @channel_cooldown(1, 300)
    async def pup(self, interaction: discord.Interaction) -> None:
        await self._show(interaction, "pup")

    @app_commands.command(description="Display next meow in sequence")
    @app_commands.guild_only()
    @outside_no_spam_channels()
    @channel_cooldown(1, 300)
    async def meow(self, interaction: discord.Interaction) -> None:
        await self._show(interaction, "meow")

    @app_commands.command(description="Display next fridge in sequence")
    @app_commands.guild_only()
    @outside_no_spam_channels()
    @channel_cooldown(1, 300)
    async def fridge(self, interaction: discord.Interaction) -> None:
        await self._show(interaction, "fridge")

    gallery = app_commands.Group(name="gallery", description="Manage the bot's image lists")

    @gallery.command(name="list", description="List all stored images of a kind")
    async def gallery_list(self, interaction: discord.Interaction, kind: Kind) -> None:
        label, _ = KIND_META[kind]
        entries = await images.list_entries(kind)
        if not entries:
            embed = discord.Embed(
                colour=discord.Colour.red(),
                title=f"No {label}s",
                description=f"There are no {kind}s. Add some with /gallery add",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await send_paginated(
            interaction,
            f"{label} List",
            f"Here are all the {kind}s!",
            [(str(entry.id), entry.url) for entry in entries],
        )

    @gallery.command(name="add", description="Add an image")
    @admin_only()
    async def gallery_add(
        self, interaction: discord.Interaction, kind: Kind, url: str, author: str, title: str
    ) -> None:
        label, _ = KIND_META[kind]
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message(
                "Invalid URL. Valid urls begin with http:// or https://", ephemeral=True
            )
            return
        if not await images.add_entry(kind, url, author, title):
            await interaction.response.send_message(
                f"Could not add {kind} {url}. It may already exist", ephemeral=True
            )
            return
        await interaction.response.send_message(f"{label} added: {title}", ephemeral=True)

    @gallery.command(name="remove", description="Remove an image by id or url")
    @admin_only()
    async def gallery_remove(
        self, interaction: discord.Interaction, kind: Kind, entry: str
    ) -> None:
        label, _ = KIND_META[kind]
        if not await images.remove_entry(kind, entry):
            await interaction.response.send_message(
                f"Could not remove {kind} {entry}. It may not exist", ephemeral=True
            )
            return
        await interaction.response.send_message(f"{label} {entry} removed", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gallery(bot))
