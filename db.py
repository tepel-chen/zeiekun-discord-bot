from sqlalchemy import TIMESTAMP, Column, Integer, Text, create_engine, select, text
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
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def get_engine():
    global _engine, _session_factory, _session_db_path
    if _engine is None or _session_db_path != DB_PATH:
        _engine = create_engine(f"sqlite:///{DB_PATH}")
        _session_factory = None
        _session_db_path = DB_PATH
    return _engine


def get_session_factory():
    global _session_factory
    engine = get_engine()
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine)
    return _session_factory


def init_database():
    Base.metadata.create_all(get_engine())


def add_channel_record(channel_id: int, guild_id: int, channel_name: str):
    session_factory = get_session_factory()
    with session_factory() as session:
        session.add(
            CTFChannel(
                channel_id=channel_id,
                guild_id=guild_id,
                channel_name=channel_name,
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
