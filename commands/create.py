import discord
from discord import app_commands

from db import add_channel_record
from services.channel_service import (
    allocate_channel_name,
    build_join_announcement,
    create_private_channel,
    ensure_category,
    get_participant_count,
)


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_creator_role_id)
    @ctf_commands.command(name="create", description="CTFチャンネルを作成する")
    @app_commands.describe(name="CTFの名前")
    async def ctf_create(interaction: discord.Interaction, name: str):
        guild = interaction.guild
        assert guild is not None, "This command must be used in a guild"

        await interaction.response.defer(ephemeral=True, thinking=True)
        category = await ensure_category(guild, context.category_name)
        final_name = allocate_channel_name(guild.text_channels, name)

        channel = await create_private_channel(guild, final_name, category)

        add_channel_record(channel.id, guild.id, final_name)

        join_custom_id = f"ctf_join:{channel.id}"
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label=f"{channel.name} に参加する",
                style=discord.ButtonStyle.primary,
                custom_id=join_custom_id,
            )
        )

        await interaction.followup.send(
            content=f"{channel.mention} ({channel.name})が作成されました",
            ephemeral=True,
        )

        try:
            if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                await interaction.channel.send(
                    content=build_join_announcement(channel, get_participant_count(channel)),
                    view=view,
                )
        except Exception:
            context.logger.exception("Failed to send join button to invoking channel")
