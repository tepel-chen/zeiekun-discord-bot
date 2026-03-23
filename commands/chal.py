import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from services.channel_service import normalize_category


@command_metadata(required_role="ctf", channel_scope="bot_ctf_channel")
def register_command(ctf_commands: app_commands.Group, context):
    """CTFチャンネル内にチャレンジ用スレッドを作成する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="chal", description="CTFチャンネルでチャレンジスレッドを作製する")
    @app_commands.describe(category="チャレンジのカテゴリ", name="チャレンジ名")
    async def ctf_chal(interaction: discord.Interaction, category: str, name: str):
        channel = interaction.channel

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
