from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, Embedding


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Problem(Base):
    __tablename__ = 'problems'
    id: Mapped[str] = mapped_column(String(90), primary_key=True)
    title: Mapped[str] = mapped_column(String(250), index=True)
    topic: Mapped[str] = mapped_column(String(80), index=True)
    subtopic: Mapped[str] = mapped_column(String(100), index=True)
    difficulty: Mapped[str] = mapped_column(String(10))
    statement: Mapped[str] = mapped_column(Text)
    hints: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    solution: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default='cpp')
    time_complexity: Mapped[str] = mapped_column(String(120), default='See source analysis')
    space_complexity: Mapped[str] = mapped_column(String(120), default='See source analysis')
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(160))
    license: Mapped[str] = mapped_column(String(40), default='MIT')
    tags: Mapped[list] = mapped_column(JSON, default=list)


class Chunk(Base):
    __tablename__ = 'chunks'
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey('problems.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Embedding(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Bookmark(Base):
    __tablename__ = 'bookmarks'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey('problems.id', ondelete='CASCADE'), primary_key=True)


class Progress(Base):
    __tablename__ = 'progress'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey('problems.id', ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default='in_progress')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    problem_id: Mapped[str | None] = mapped_column(ForeignKey('problems.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(20))
    citations: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(30), default='local')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
