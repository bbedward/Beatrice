import discord
from discord import app_commands

from beatrice.config import Settings


def is_admin(settings: Settings, user: discord.Member | discord.User) -> bool:
    if user.id in settings.admin_user_ids:
        return True
    roles = getattr(user, "roles", ())
    return any(role.id in settings.admin_role_ids for role in roles)


def admin_only():
    def predicate(interaction: discord.Interaction) -> bool:
        return is_admin(interaction.client.settings, interaction.user)

    return app_commands.check(predicate)


def outside_no_spam_channels():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id not in interaction.client.settings.no_spam_channel_ids

    return app_commands.check(predicate)


def _cooldown_factory(rate: int, per: float):
    def factory(interaction: discord.Interaction) -> app_commands.Cooldown | None:
        if interaction.user.id in interaction.client.settings.super_user_ids:
            return None
        return app_commands.Cooldown(rate, per)

    return factory


def channel_cooldown(rate: int, per: float):
    # Buckets are cached per key before the factory can exempt anyone, so super
    # users need their own key to keep them off the shared channel bucket.
    def key(interaction: discord.Interaction):
        if interaction.user.id in interaction.client.settings.super_user_ids:
            return ("super", interaction.user.id)
        return ("channel", interaction.channel_id)

    return app_commands.checks.dynamic_cooldown(_cooldown_factory(rate, per), key=key)


def user_cooldown(rate: int, per: float):
    return app_commands.checks.dynamic_cooldown(
        _cooldown_factory(rate, per), key=lambda interaction: interaction.user.id
    )
