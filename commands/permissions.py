from collections.abc import Callable

import discord
from discord import app_commands

from db import is_bot_created_channel
from interaction_errors import UserFacingCheckFailure


def command_metadata(*, required_role: str | None, channel_scope: str = "any"):
    def decorator(register_fn):
        register_fn.required_role = required_role
        register_fn.channel_scope = channel_scope
        return register_fn

    return decorator


def can_use_command(interaction: discord.Interaction, required_role: str | None, context) -> bool:
    if required_role is None:
        return True

    role_ids = {role.id for role in getattr(interaction.user, "roles", [])}
    if required_role == "ctf":
        return context.ctf_role_id in role_ids
    if required_role == "creator":
        return context.ctf_creator_role_id in role_ids
    return False


def matches_channel_scope(interaction: discord.Interaction, channel_scope: str, context) -> bool:
    channel = interaction.channel
    if channel_scope == "any":
        return True
    if channel_scope == "outside_ctf_channel":
        return not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id)
    if channel_scope == "bot_ctf_channel":
        return isinstance(channel, discord.TextChannel) and is_bot_created_channel(channel.id)
    if channel_scope == "bot_ctf_channel_or_thread":
        if isinstance(channel, discord.TextChannel):
            return is_bot_created_channel(channel.id)
        if isinstance(channel, discord.Thread):
            return channel.parent_id is not None and is_bot_created_channel(channel.parent_id)
        return False
    if channel_scope == "bot_ctf_thread":
        return isinstance(channel, discord.Thread) and channel.owner_id == context.bot.user.id
    return False


def can_use_command_in_context(interaction: discord.Interaction, register_fn, context) -> bool:
    required_role = getattr(register_fn, "required_role", None)
    channel_scope = getattr(register_fn, "channel_scope", "any")
    return can_use_command(interaction, required_role, context) and matches_channel_scope(
        interaction,
        channel_scope,
        context,
    )


def get_channel_scope_error(interaction: discord.Interaction, channel_scope: str, context) -> str:
    channel = interaction.channel
    if channel_scope == "outside_ctf_channel":
        return "❌ このコマンドはbotによって作成されたチャンネル内では使用できません。"
    if channel_scope == "bot_ctf_channel":
        return "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。"
    if channel_scope == "bot_ctf_channel_or_thread":
        return "❌ このコマンドはbotによって作成されたチャンネルまたはそのスレッドでのみ使用できます。"
    if channel_scope == "bot_ctf_thread":
        if not isinstance(channel, discord.Thread):
            return "❌ このコマンドはスレッド内でのみ使用できます。"
        return "❌ このスレッドは bot が作成したものではありません。"
    return "❌ このコマンドはここでは使用できません。"


def require_registered_role(register_fn, context) -> Callable:
    required_role = getattr(register_fn, "required_role", None)

    async def predicate(interaction: discord.Interaction) -> bool:
        if can_use_command(interaction, required_role, context):
            return True
        raise UserFacingCheckFailure("❌ このコマンドを実行する権限がありません。")

    return app_commands.check(predicate)


def require_registered_context(register_fn, context) -> Callable:
    channel_scope = getattr(register_fn, "channel_scope", "any")

    async def predicate(interaction: discord.Interaction) -> bool:
        if matches_channel_scope(interaction, channel_scope, context):
            return True
        raise UserFacingCheckFailure(get_channel_scope_error(interaction, channel_scope, context))

    return app_commands.check(predicate)
