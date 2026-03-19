import importlib
import sys
from datetime import datetime
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
    db.add_channel_record(
        1001,
        2002,
        "ctf-sample",
        start_time=datetime(2026, 3, 20, 10, 0),
        end_time=datetime(2026, 3, 21, 12, 0),
    )

    assert db_path.exists()
    assert db.is_bot_created_channel(1001) is True
    assert db.is_bot_created_channel(9999) is False
    record = db.get_channel_record(1001)
    assert record.start_time == datetime(2026, 3, 20, 10, 0)
    assert record.end_time == datetime(2026, 3, 21, 12, 0)
    assert record.root_channel_id == 1001
    assert record.team_mode == "auto"

    assert db.update_channel_record(1001, start_time=datetime(2026, 3, 20, 11, 0)) is True
    updated = db.get_channel_record(1001)
    assert updated.start_time == datetime(2026, 3, 20, 11, 0)

    db.upsert_participant_record(1001, 10, "play2win")
    db.upsert_participant_record(1001, 20, "play4fun")
    db.upsert_participant_record(1001, 10, "play4fun")
    participants = db.get_participants(1001)
    assert [(participant.user_id, participant.participation_type) for participant in participants] == [
        (10, "play4fun"),
        (20, "play4fun"),
    ]
