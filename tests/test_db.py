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
    assert record.archived == 0

    assert db.update_channel_record(1001, start_time=datetime(2026, 3, 20, 11, 0)) is True
    updated = db.get_channel_record(1001)
    assert updated.start_time == datetime(2026, 3, 20, 11, 0)

    assert db.update_channel_record(1001, archived=1) is True
    updated = db.get_channel_record(1001)
    assert updated.archived == 1
    assert db.get_channels_pending_split(datetime(2026, 3, 20, 9, 0)) == []

    db.upsert_participant_record(1001, 10, "play2win")
    db.upsert_participant_record(1001, 20, "play4fun")
    db.upsert_participant_record(1001, 10, "play4fun")
    participants = db.get_participants(1001)
    assert [(participant.user_id, participant.participation_type) for participant in participants] == [
        (10, "play4fun"),
        (20, "play4fun"),
    ]


def test_database_team_helpers_and_deletes(tmp_path):
    sys.modules.pop("db", None)
    db = importlib.import_module("db")
    db_path = tmp_path / "ctf_channels.db"
    db.DB_PATH = str(db_path)

    db.init_database()
    db.add_channel_record(1001, 2002, "ctf-root", start_time=datetime(2026, 3, 20, 10, 0))
    db.add_channel_record(
        1002,
        2002,
        "ctf-root-p2w",
        root_channel_id=1001,
        team_type="play2win",
        split_completed=1,
    )

    assert db.get_root_channel_record(1002).channel_id == 1001
    assert db.get_root_channel_record(9999) is None
    assert db.get_team_channel_record(1001, "play2win").channel_id == 1002
    assert db.get_team_channel_record(1001, "play4fun") is None
    assert [record.channel_id for record in db.get_team_channels(1001)] == [1002]
    assert db.update_channel_record(9999, archived=1) is False
    assert db.delete_channel_record(1002) is True
    assert db.delete_channel_record(1002) is False
    assert db.get_channel_record(1002) is None


def test_database_participant_helpers_without_root_record(tmp_path):
    sys.modules.pop("db", None)
    db = importlib.import_module("db")
    db_path = tmp_path / "ctf_channels.db"
    db.DB_PATH = str(db_path)

    db.init_database()
    db.upsert_participant_record(7777, 10, "play2win")

    participant = db.get_participant(7777, 10)
    assert participant is not None
    assert participant.participation_type == "play2win"
    assert db.get_participant(7777, 20) is None
    assert [item.user_id for item in db.get_participants(7777)] == [10]
