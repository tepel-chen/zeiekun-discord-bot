import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_database_helpers(tmp_path):
    sys.modules.pop("db", None)
    db = importlib.import_module("db")
    db_path = tmp_path / "ctf_channels.db"
    db.DB_PATH = str(db_path)

    db.init_database()
    db.add_channel_record(1001, 2002, "ctf-sample")

    assert db_path.exists()
    assert db.is_bot_created_channel(1001) is True
    assert db.is_bot_created_channel(9999) is False
