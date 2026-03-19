from dataclasses import dataclass
import logging

import discord


@dataclass(frozen=True)
class CommandContext:
    bot: discord.Client
    logger: logging.Logger
    category_name: str
    archive_category: str
    ctf_creator_role_id: int
    ctf_role_id: int
