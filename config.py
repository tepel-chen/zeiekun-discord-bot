import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int
    ctf_creator_role_id: int
    ctf_role_id: int
    category_name: str
    archive_category: str


def load_settings() -> Settings:
    return Settings(
        token=os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN"),
        guild_id=int(os.getenv("DISCORD_GUILD_ID", "0")),
        ctf_creator_role_id=int(os.getenv("CTF_CREATOR_ROLE_ID", "0")),
        ctf_role_id=int(os.getenv("CTF_ROLE_ID", "0")),
        category_name=os.getenv("CTF_CATEGORY", "CTF"),
        archive_category=os.getenv("ARCHIVE_CATEGORY", "ARCHIVE"),
    )
