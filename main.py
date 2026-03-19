import logging

from dotenv import load_dotenv

from app import create_application
from config import load_settings

load_dotenv(verbose=True)

logging.basicConfig(level=logging.INFO)
settings = load_settings()
bot, tree, ctf_commands, join_service = create_application(settings)

if __name__ == "__main__":
    if not settings.token or settings.token == "YOUR_BOT_TOKEN":
        raise SystemExit("Please set DISCORD_TOKEN env var")
    bot.run(settings.token)
