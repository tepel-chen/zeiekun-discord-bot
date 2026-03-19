from typing import Optional

import discord
from discord import app_commands

from db import is_bot_created_channel
from services.channel_service import (
    build_missing_search_response,
    build_search_response,
    filter_threads,
    normalize_category,
)


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
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
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            await interaction.response.send_message(
                "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
                ephemeral=True,
            )
            return

        search_category = normalize_category(category) if category else None

        matching_threads = []
        async for thread in channel.archived_threads(limit=None):
            matching_threads.append(thread)
        matching_threads.extend(channel.threads)
        matching_threads = filter_threads(matching_threads, search_category, solved)

        if not matching_threads:
            await interaction.response.send_message(
                build_missing_search_response(search_category, solved),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(build_search_response(matching_threads), ephemeral=True)
