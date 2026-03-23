import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from db import get_root_channel_record
from interaction_errors import UserFacingError
from services.split_service import SplitService
from services.time_service import tokyo_now


@command_metadata(required_role="creator", channel_scope="bot_ctf_channel")
def register_command(ctf_commands: app_commands.Group, context):
    """CTF終了後に両チームのチャンネルを相互公開する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="disclose", description="終了後に両チームのチャンネルを相互公開する")
    async def ctf_disclose(interaction: discord.Interaction):
        channel = interaction.channel

        root_record = get_root_channel_record(channel.id)
        if root_record is None:
            raise UserFacingError("❌ CTF設定が見つかりません。")
        if root_record.end_time is None or tokyo_now() < root_record.end_time:
            raise UserFacingError("❌ このコマンドは終了時刻以降にのみ実行できます。")
        if getattr(root_record, "disclosed", 0):
            raise UserFacingError("❌ このCTFはすでに disclose 済みです。")
        if interaction.guild is None:
            raise UserFacingError("This only works inside a server.")

        split_service = SplitService(context.bot, context.logger)
        disclosed = await split_service.disclose_channel(interaction.guild, root_record.channel_id)
        if not disclosed:
            raise UserFacingError("❌ disclose に失敗しました。")

        await interaction.response.send_message(
            "✅ disclose しました。",
            ephemeral=True,
        )
        await channel.send(f"{interaction.user.mention} が disclose しました。")
