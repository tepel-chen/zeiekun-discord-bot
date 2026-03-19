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
    start_time = Column(TIMESTAMP, nullable=True)
    end_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


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
                start_time=start_time,
                end_time=end_time,
            )
        )
        session.commit()


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


UPDATE_UNSET = object()


def update_channel_record(
    channel_id: int,
    *,
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

        if start_time is not UPDATE_UNSET:
            record.start_time = start_time
        if end_time is not UPDATE_UNSET:
            record.end_time = end_time

        session.commit()
        return True
