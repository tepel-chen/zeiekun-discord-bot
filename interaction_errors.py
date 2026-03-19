import discord
from discord import app_commands


class UserFacingError(Exception):
    pass


def format_interaction_error(error: Exception) -> str:
    if isinstance(error, app_commands.CommandInvokeError) and error.original is not None:
        error = error.original
    if isinstance(error, discord.Forbidden):
        return "その操作をする権限がありません"
    if isinstance(error, UserFacingError):
        return str(error)
    return f"エラー: {error}"


async def send_interaction_error(interaction: discord.Interaction, error: Exception | str):
    message = error if isinstance(error, str) else format_interaction_error(error)
    response = getattr(interaction, "response", None)
    followup = getattr(interaction, "followup", None)
    if response is not None and hasattr(response, "is_done") and response.is_done():
        if followup is not None:
            await followup.send(message, ephemeral=True)
        return

    if response is not None and hasattr(response, "send_message"):
        await response.send_message(message, ephemeral=True)
        return

    if followup is not None:
        await followup.send(message, ephemeral=True)
