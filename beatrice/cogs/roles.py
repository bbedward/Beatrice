import discord
from discord import app_commands
from discord.ext import commands

from beatrice.checks import admin_only


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _role(self, interaction: discord.Interaction, role_id: int) -> discord.Role | None:
        return interaction.guild.get_role(role_id)

    @staticmethod
    async def _missing_role(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Configured role not found.", ephemeral=True)

    @app_commands.command(description="Arrest a user")
    @app_commands.guild_only()
    @admin_only()
    async def arrest(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        jail_role = self._role(interaction, settings.arrest_role_id)
        if jail_role is None:
            await self._missing_role(interaction)
            return
        await user.add_roles(jail_role)
        jail_channel = interaction.guild.get_channel(settings.jail_channel_id)
        if jail_channel is not None:
            await jail_channel.send(f"<@{user.id}> \n{settings.msg_rights}")
        await interaction.response.send_message(f"🚔 <@{user.id}> has been arrested")

    @app_commands.command(description="Release a user from jail")
    @app_commands.guild_only()
    @admin_only()
    async def release(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        jail_role = self._role(interaction, settings.arrest_role_id)
        if jail_role is None:
            await self._missing_role(interaction)
            return
        await user.remove_roles(jail_role)
        await interaction.response.send_message(f"<@{user.id}> \n{settings.msg_release}")

    @app_commands.command(description="Mark a user as a troll")
    @app_commands.guild_only()
    @admin_only()
    async def troll(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        troll_role = self._role(interaction, settings.troll_role_id)
        citizen_role = self._role(interaction, settings.citizen_role_id)
        if troll_role is None or citizen_role is None:
            await self._missing_role(interaction)
            return
        await user.add_roles(troll_role)
        await user.remove_roles(citizen_role)
        await interaction.response.send_message(f"<@{user.id}> \n{settings.msg_troll}")

    @app_commands.command(description="Remove the troll mark from a user")
    @app_commands.guild_only()
    @admin_only()
    async def untroll(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        troll_role = self._role(interaction, settings.troll_role_id)
        if troll_role is None:
            await self._missing_role(interaction)
            return
        await user.remove_roles(troll_role)
        await interaction.response.send_message(f"<@{user.id}> \n{settings.msg_untroll}")

    @app_commands.command(description="Grant citizenship to a user")
    @app_commands.guild_only()
    @admin_only()
    async def citizenship(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        citizen_role = self._role(interaction, settings.citizen_role_id)
        if citizen_role is None:
            await self._missing_role(interaction)
            return
        await user.add_roles(citizen_role)
        await interaction.response.send_message(f"<@{user.id}> \n{settings.msg_citizenship}")

    @app_commands.command(description="Revoke a user's citizenship")
    @app_commands.guild_only()
    @admin_only()
    async def deport(self, interaction: discord.Interaction, user: discord.Member) -> None:
        settings = self.bot.settings
        citizen_role = self._role(interaction, settings.citizen_role_id)
        if citizen_role is None:
            await self._missing_role(interaction)
            return
        await user.remove_roles(citizen_role)
        await interaction.response.send_message(f"<@{user.id}> \n{settings.msg_deport}")

    images = app_commands.Group(
        name="images",
        description="Control a user's image posting permission",
        guild_only=True,
    )

    @images.command(name="deny", description="Stop a user posting images")
    @admin_only()
    async def images_deny(self, interaction: discord.Interaction, user: discord.Member) -> None:
        role = self._role(interaction, self.bot.settings.images_role_id)
        if role is None:
            await self._missing_role(interaction)
            return
        await user.add_roles(role)
        await interaction.response.send_message(
            f"💅 <@{user.id}> can no longer post images", ephemeral=True
        )

    @images.command(name="allow", description="Allow a user to post images")
    @admin_only()
    async def images_allow(self, interaction: discord.Interaction, user: discord.Member) -> None:
        role = self._role(interaction, self.bot.settings.images_role_id)
        if role is None:
            await self._missing_role(interaction)
            return
        await user.remove_roles(role)
        await interaction.response.send_message(
            f"🎨 <@{user.id}> can post images again", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
