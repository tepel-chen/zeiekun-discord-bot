import discord
from discord import app_commands

from db import get_root_channel_record, is_bot_created_channel
from interaction_errors import UserFacingError
from services.split_service import SplitService
from services.time_service import tokyo_now


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_creator_role_id)
    @ctf_commands.command(name="disclose", description="終了後に両チームのチャンネルを相互公開する")
    async def ctf_disclose(interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            raise UserFacingError("❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。")

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
