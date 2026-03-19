from datetime import datetime

import discord
from discord import app_commands

from db import get_root_channel_record, is_bot_created_channel
from services.time_service import build_time_response


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
    @ctf_commands.command(name="time", description="CTFの開始終了時刻を確認する")
    async def ctf_time(interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            await interaction.response.send_message(
                "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
                ephemeral=True,
            )
            return

        record = get_root_channel_record(channel.id)
        if record is None:
            await interaction.response.send_message(
                "❌ CTF設定が見つかりません。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            build_time_response(
                record.channel_name,
                record.start_time,
                record.end_time,
                datetime.now(),
            ),
            ephemeral=True,
        )
