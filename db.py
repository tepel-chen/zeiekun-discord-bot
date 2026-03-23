from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import TIMESTAMP, Column, Integer, Text, create_engine, inspect, select, text
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = "ctf_channels.db"
Base = declarative_base()
_engine = None
_session_factory = None
_session_db_path = None


class CTFChannel(Base):
    __tablename__ = "ctf_channels"

    channel_id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    channel_name = Column(Text, nullable=False)
    root_channel_id = Column(Integer, nullable=False)
    team_type = Column(Text, nullable=False, server_default=text("'all'"))
    team_mode = Column(Text, nullable=False, server_default=text("'auto'"))
    split_completed = Column(Integer, nullable=False, server_default=text("0"))
    archived = Column(Integer, nullable=False, server_default=text("0"))
    disclosed = Column(Integer, nullable=False, server_default=text("0"))
    start_time = Column(TIMESTAMP, nullable=True)
    end_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class CTFParticipant(Base):
    __tablename__ = "ctf_participants"

    channel_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    participation_type = Column(Text, nullable=False)
    joined_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def get_engine():
    global _engine, _session_factory, _session_db_path
    if _engine is None or _session_db_path != DB_PATH:
        _engine = create_engine(f"sqlite:///{DB_PATH}")
        _session_factory = None
        _session_db_path = DB_PATH
    return _engine


def get_database_url() -> str:
    return f"sqlite:///{DB_PATH}"


def get_alembic_config() -> Config:
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    config.set_main_option("script_location", str(Path(__file__).with_name("alembic")))
    config.set_main_option("sqlalchemy.url", get_database_url())
    return config


def get_session_factory():
    global _session_factory
    engine = get_engine()
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory


def init_database():
    command.upgrade(get_alembic_config(), "head")


def add_channel_record(
    channel_id: int,
    guild_id: int,
    channel_name: str,
    root_channel_id: int | None = None,
    team_type: str = "all",
    team_mode: str = "auto",
    split_completed: int = 0,
    archived: int = 0,
    disclosed: int = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    session_factory = get_session_factory()
    with session_factory() as session:
        session.add(
            CTFChannel(
                channel_id=channel_id,
                guild_id=guild_id,
                channel_name=channel_name,
                root_channel_id=root_channel_id or channel_id,
                team_type=team_type,
                team_mode=team_mode,
                split_completed=split_completed,
                archived=archived,
                disclosed=disclosed,
                start_time=start_time,
                end_time=end_time,
            )
        )
        session.commit()


def delete_channel_record(channel_id: int) -> bool:
    session_factory = get_session_factory()
    with session_factory() as session:
        record = session.execute(
            select(CTFChannel).where(CTFChannel.channel_id == channel_id)
        ).scalar_one_or_none()
        if record is None:
            return False
        session.delete(record)
        session.commit()
        return True


def is_bot_created_channel(channel_id: int) -> bool:
    session_factory = get_session_factory()
    with session_factory() as session:
        result = session.execute(
            select(CTFChannel.channel_id).where(CTFChannel.channel_id == channel_id)
        ).scalar_one_or_none()
        return result is not None


def get_channel_record(channel_id: int) -> CTFChannel | None:
    session_factory = get_session_factory()
    with session_factory() as session:
        return session.execute(
            select(CTFChannel).where(CTFChannel.channel_id == channel_id)
        ).scalar_one_or_none()


def get_root_channel_record(channel_id: int) -> CTFChannel | None:
    session_factory = get_session_factory()
    with session_factory() as session:
        record = session.execute(
            select(CTFChannel).where(CTFChannel.channel_id == channel_id)
        ).scalar_one_or_none()
        if record is None:
            return None
        if record.root_channel_id == record.channel_id:
            return record
        return session.execute(
            select(CTFChannel).where(CTFChannel.channel_id == record.root_channel_id)
        ).scalar_one_or_none()


def get_team_channel_record(root_channel_id: int, team_type: str) -> CTFChannel | None:
    session_factory = get_session_factory()
    with session_factory() as session:
        return session.execute(
            select(CTFChannel).where(
                CTFChannel.root_channel_id == root_channel_id,
                CTFChannel.team_type == team_type,
            )
        ).scalar_one_or_none()


def get_channels_pending_split(now: datetime) -> list[CTFChannel]:
    session_factory = get_session_factory()
    with session_factory() as session:
        return list(
            session.execute(
                select(CTFChannel).where(
                    CTFChannel.root_channel_id == CTFChannel.channel_id,
                    CTFChannel.team_type == "all",
                    CTFChannel.split_completed == 0,
                    CTFChannel.archived == 0,
                    CTFChannel.start_time.is_not(None),
                )
            ).scalars()
        )


def get_team_channels(root_channel_id: int) -> list[CTFChannel]:
    session_factory = get_session_factory()
    with session_factory() as session:
        return list(
            session.execute(
                select(CTFChannel).where(
                    CTFChannel.root_channel_id == root_channel_id,
                    CTFChannel.channel_id != root_channel_id,
                )
            ).scalars()
        )


UPDATE_UNSET = object()


def update_channel_record(
    channel_id: int,
    *,
    channel_name: str | object = UPDATE_UNSET,
    team_type: str | object = UPDATE_UNSET,
    team_mode: str | object = UPDATE_UNSET,
    split_completed: int | object = UPDATE_UNSET,
    archived: int | object = UPDATE_UNSET,
    disclosed: int | object = UPDATE_UNSET,
    start_time: datetime | None | object = UPDATE_UNSET,
    end_time: datetime | None | object = UPDATE_UNSET,
) -> bool:
    session_factory = get_session_factory()
    with session_factory() as session:
        record = session.execute(
            select(CTFChannel).where(CTFChannel.channel_id == channel_id)
        ).scalar_one_or_none()
        if record is None:
            return False

        if channel_name is not UPDATE_UNSET:
            record.channel_name = channel_name
        if team_type is not UPDATE_UNSET:
            record.team_type = team_type
        if team_mode is not UPDATE_UNSET:
            record.team_mode = team_mode
        if split_completed is not UPDATE_UNSET:
            record.split_completed = split_completed
        if archived is not UPDATE_UNSET:
            record.archived = archived
        if disclosed is not UPDATE_UNSET:
            record.disclosed = disclosed
        if start_time is not UPDATE_UNSET:
            record.start_time = start_time
        if end_time is not UPDATE_UNSET:
            record.end_time = end_time

        session.commit()
        return True


def upsert_participant_record(channel_id: int, user_id: int, participation_type: str):
    root_record = get_root_channel_record(channel_id)
    root_channel_id = root_record.channel_id if root_record is not None else channel_id
    session_factory = get_session_factory()
    with session_factory() as session:
        record = session.execute(
            select(CTFParticipant).where(
                CTFParticipant.channel_id == root_channel_id,
                CTFParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()
        if record is None:
            session.add(
                CTFParticipant(
                    channel_id=root_channel_id,
                    user_id=user_id,
                    participation_type=participation_type,
                )
            )
        else:
            record.participation_type = participation_type
        session.commit()


def get_participants(channel_id: int) -> list[CTFParticipant]:
    root_record = get_root_channel_record(channel_id)
    root_channel_id = root_record.channel_id if root_record is not None else channel_id
    session_factory = get_session_factory()
    with session_factory() as session:
        return list(
            session.execute(
                select(CTFParticipant)
                .where(CTFParticipant.channel_id == root_channel_id)
                .order_by(CTFParticipant.joined_at.asc(), CTFParticipant.user_id.asc())
            ).scalars()
        )


def get_participant(channel_id: int, user_id: int) -> CTFParticipant | None:
    root_record = get_root_channel_record(channel_id)
    root_channel_id = root_record.channel_id if root_record is not None else channel_id
    session_factory = get_session_factory()
    with session_factory() as session:
        return session.execute(
            select(CTFParticipant).where(
                CTFParticipant.channel_id == root_channel_id,
                CTFParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()


def delete_participant_record(channel_id: int, user_id: int) -> bool:
    root_record = get_root_channel_record(channel_id)
    root_channel_id = root_record.channel_id if root_record is not None else channel_id
    session_factory = get_session_factory()
    with session_factory() as session:
        record = session.execute(
            select(CTFParticipant).where(
                CTFParticipant.channel_id == root_channel_id,
                CTFParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return False
        session.delete(record)
        session.commit()
        return True
