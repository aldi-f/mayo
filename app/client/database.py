import logging

from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

logger = logging.getLogger("discord")


engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(engine)

class Base(DeclarativeBase):
    pass


class Servers(Base):
    __tablename__ = "servers"
    server_id: Mapped[str] = mapped_column(primary_key=True)
    chat_model: Mapped[str] = mapped_column(default=settings.BASE_MODEL)
    chat_system_prompt: Mapped[str] = mapped_column(default=settings.BASE_SYSTEM_PROMPT)
    chat_temperature: Mapped[float] = mapped_column(default=1.0)
    chat_total_cost: Mapped[float] = mapped_column(default=0.0)


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    chat_model: Mapped[str] = mapped_column(default=settings.BASE_MODEL)
    chat_system_prompt: Mapped[str] = mapped_column(default=settings.BASE_SYSTEM_PROMPT)
    chat_temperature: Mapped[float] = mapped_column(default=1.0)
    chat_total_cost: Mapped[float] = mapped_column(default=0.0)
    grok_model: Mapped[str] = mapped_column(default=settings.GROK_MODEL)
    grok_system_prompt: Mapped[str] = mapped_column(
        default=settings.BASE_GROK_SYSTEM_PROMPT
    )
    grok_temperature: Mapped[float] = mapped_column(default=1.0)
    grok_total_cost: Mapped[float] = mapped_column(default=0.0)


def init_db():
    with engine.connect():  # just to start it
        Base.metadata.create_all(engine)


def get_or_create_server(server_id: str) -> Servers:
    with Session() as session:
        server = session.get(Servers, server_id)
        if not server:
            server = Servers(server_id=server_id)
            session.add(server)
            session.commit()
        return server

def get_or_create_user(user_id: str) -> UserSettings:
    with Session() as session:
        user = session.get(UserSettings, user_id)
        if not user:
            user = UserSettings(user_id=user_id)
            session.add(user)
            session.commit()
        return user
