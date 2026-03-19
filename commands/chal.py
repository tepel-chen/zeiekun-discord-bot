import discord
from discord import app_commands

from db import is_bot_created_channel
from interaction_errors import UserFacingError
from services.channel_service import normalize_category


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
    @ctf_commands.command(name="chal", description="CTFチャンネルでチャレンジスレッドを作製する")
    @app_commands.describe(category="チャレンジのカテゴリ", name="チャレンジ名")
    async def ctf_chal(interaction: discord.Interaction, category: str, name: str):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            raise UserFacingError("❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。")

        normalized_category = normalize_category(category)
        await interaction.channel.create_thread(
            name=f"{name} [{normalized_category}]",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60,
        )
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} さんがスレッドを作成しました",
            ephemeral=False,
        )
