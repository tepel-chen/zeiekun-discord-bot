import discord
from discord import app_commands

from db import get_root_channel_record, get_team_channels, is_bot_created_channel, update_channel_record
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
        root_record = get_root_channel_record(channel.id)
        target_channels = [channel]
        seen_ids = {channel.id}
        if root_record is not None:
            root_channel = guild.get_channel(root_record.channel_id)
            if isinstance(root_channel, discord.TextChannel) and root_channel.id not in seen_ids:
                target_channels.append(root_channel)
                seen_ids.add(root_channel.id)
            for team_record in get_team_channels(root_record.channel_id):
                team_channel = guild.get_channel(team_record.channel_id)
                if isinstance(team_channel, discord.TextChannel) and team_channel.id not in seen_ids:
                    target_channels.append(team_channel)
                    seen_ids.add(team_channel.id)

        for target_channel in target_channels:
            await target_channel.edit(category=category)
            update_channel_record(target_channel.id, archived=1)

        await interaction.response.send_message(
            f"✅ チャンネル {channel.mention} をカテゴリー「{context.archive_category}」へ移動しました。"
        )
        await channel.send(
            f"{interaction.user.mention} がこの CTF をアーカイブしました。"
        )
