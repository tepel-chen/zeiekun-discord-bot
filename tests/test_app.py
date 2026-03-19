import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_create_application_registers_ctf_group():
    config = importlib.import_module("config")
    app = importlib.import_module("app")

    settings = config.Settings(
        token="token",
        guild_id=123,
        ctf_creator_role_id=1,
        ctf_role_id=2,
        category_name="CTF",
        archive_category="ARCHIVE",
    )

    bot, tree, ctf_commands, join_service = app.create_application(settings)

    assert bot is not None
    assert tree is not None
    assert ctf_commands.name == "ctf"
    assert join_service.ctf_role_id == 2


def test_main_imports_with_factory():
    sys.modules.pop("main", None)
    module = importlib.import_module("main")

    assert module.bot is not None
    assert module.settings is not None
