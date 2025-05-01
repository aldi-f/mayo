from typing import Any
import logging
from sqlalchemy import create_engine
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.mutable import MutableDict, MutableList
from app.config import BASE_SYSTEM_PROMPT

logger = logging.getLogger('discord')

DATABASE_PATH = "/data/mayo.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
session_factory = sessionmaker(engine)
Session = scoped_session(session_factory)


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: MutableDict.as_mutable(JSON),
        list[int]: MutableList.as_mutable(JSON),
        list[str]: MutableList.as_mutable(JSON)
    }
class Servers(Base):
    __tablename__ = "servers"

    server_id: Mapped[str] = mapped_column(primary_key=True)
    server_name: Mapped[str] = mapped_column(nullable=True)
    model: Mapped[str] = mapped_column(default="google/gemini-2.0-flash-001")
    system_prompt: Mapped[str] = mapped_column(default=BASE_SYSTEM_PROMPT)

def init_db():
    with engine.connect(): # just to start it
        Base.metadata.create_all(engine)
    