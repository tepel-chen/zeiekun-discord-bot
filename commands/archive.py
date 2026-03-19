import discord
from discord import app_commands

from db import is_bot_created_channel
from interaction_errors import UserFacingError
from services.channel_service import ensure_category


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_creator_role_id)
    @ctf_commands.command(name="archive", description="CTFチャンネルをアーカイブする")
    async def move_category(interaction: discord.Interaction):
        guild = interaction.guild
        assert guild is not None, "This command must be used in a guild"
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            raise UserFacingError("❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。")

        category = await ensure_category(guild, context.archive_category)
        await channel.edit(category=category)
        await interaction.response.send_message(
            f"✅ チャンネル {channel.mention} をカテゴリー「{context.archive_category}」へ移動しました。"
        )
