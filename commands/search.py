from typing import Optional

import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from interaction_errors import UserFacingError
from services.channel_service import (
    build_missing_search_response,
    build_search_response,
    filter_threads,
    normalize_category,
)


@command_metadata(required_role="ctf", channel_scope="bot_ctf_channel_or_thread")
def register_command(ctf_commands: app_commands.Group, context):
    """カテゴリや解決状態でスレッドを検索する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="search", description="カテゴリ名でスレッドを検索する")
    @app_commands.describe(
        category="検索するカテゴリ名（未指定の場合は全カテゴリ）",
        solved="解決済み(True)/未解決(False)/両方(未指定)",
    )
    async def ctf_search(
        interaction: discord.Interaction,
        category: Optional[str] = None,
        solved: Optional[bool] = None,
    ):
        channel = interaction.channel
        target_channel = channel.parent if isinstance(channel, discord.Thread) else channel

        search_category = normalize_category(category) if category else None

        matching_threads = []
        async for thread in target_channel.archived_threads(limit=None):
            matching_threads.append(thread)
        matching_threads.extend(target_channel.threads)
        matching_threads = filter_threads(matching_threads, search_category, solved)

        if not matching_threads:
            raise UserFacingError(build_missing_search_response(search_category, solved))

        await interaction.response.send_message(build_search_response(matching_threads), ephemeral=True)
