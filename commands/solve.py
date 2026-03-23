import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role


@command_metadata(required_role="ctf", channel_scope="bot_ctf_thread")
def register_command(ctf_commands: app_commands.Group, context):
    """チャレンジスレッドを解決済み状態に変更する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="solve", description="CTFチャンネルのチャレンジスレッドを完了状態にする")
    async def ctf_solve(interaction: discord.Interaction):
        channel = interaction.channel

        if not channel.name.startswith("✅"):
            await channel.edit(name=f"✅ {channel.name}")
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} さんがスレッドを解決済みにしました！",
                ephemeral=False,
            )
        else:
            await interaction.response.send_message("⚠️ すでに解決済みです。", ephemeral=True)
