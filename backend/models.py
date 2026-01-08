from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String(64), unique=True, nullable=False, index=True)
    profile = Column(JSON, nullable=True)

    chat_sessions = relationship("ChatSession", back_populates="user")


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(64), unique=True, nullable=True, index=True)
    code = Column(String(64), unique=True, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="assistant")


class ChatSession(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    assistant = relationship("Assistant", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column('conversation_id', Integer, ForeignKey("conversations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
