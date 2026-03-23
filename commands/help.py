import inspect

import discord
from discord import app_commands

from commands.permissions import can_use_command, can_use_command_in_context, command_metadata

def build_command_help_field(register_fn) -> tuple[str, str]:
    name = inspect.getmodule(register_fn).__name__.rsplit(".", 1)[-1]
    description = inspect.getdoc(register_fn) or "説明は未設定です。"
    return f"/ctf {name}", description


@command_metadata(required_role=None, channel_scope="any")
def register_command(ctf_commands: app_commands.Group, context):
    """利用できる /ctf コマンドを一覧表示する。"""

    @ctf_commands.command(name="help", description="利用できる /ctf コマンド一覧を表示する")
    @app_commands.describe(all="実行場所を無視して利用可能コマンドをすべて表示する")
    async def ctf_help(interaction: discord.Interaction, all: bool = False):
        from commands.registry import COMMAND_REGISTRARS

        embed = discord.Embed(
            title="/ctf help",
            description="利用できるコマンド一覧" if not all else "利用できるコマンド一覧 (全表示)",
            color=discord.Color.blue(),
        )
        for register_fn in COMMAND_REGISTRARS:
            required_role = getattr(register_fn, "required_role", None)
            if not can_use_command(interaction, required_role, context):
                continue
            if not all and not can_use_command_in_context(interaction, register_fn, context):
                continue
            name, description = build_command_help_field(register_fn)
            embed.add_field(name=name, value=description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
