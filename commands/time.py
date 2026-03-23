import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from db import get_root_channel_record
from interaction_errors import UserFacingError
from services.time_service import build_time_response, tokyo_now


@command_metadata(required_role="ctf", channel_scope="bot_ctf_channel_or_thread")
def register_command(ctf_commands: app_commands.Group, context):
    """CTFの開始時刻と終了時刻を表示する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="time", description="CTFの開始終了時刻を確認する")
    async def ctf_time(interaction: discord.Interaction):
        channel = interaction.channel
        target_channel_id = channel.parent_id if isinstance(channel, discord.Thread) else channel.id

        record = get_root_channel_record(target_channel_id)
        if record is None:
            raise UserFacingError("❌ CTF設定が見つかりません。")

        await interaction.response.send_message(
            build_time_response(
                record.channel_name,
                record.start_time,
                record.end_time,
                tokyo_now(),
            ),
            ephemeral=True,
        )
