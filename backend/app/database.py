from sqlalchemy import create_engine, event, JSON, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector
from .config import get_settings

url = get_settings().database_url
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql+psycopg://', 1)
elif url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)

engine = create_engine(url, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {}))
SessionLocal = sessionmaker(engine, expire_on_commit=False)

if url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')


class Base(DeclarativeBase):
    pass


class Embedding(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(Vector(768) if dialect.name == 'postgresql' else JSON())


def init_db():
    if engine.dialect.name == 'postgresql':
        with engine.begin() as connection:
            connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    Base.metadata.create_all(engine)
    if engine.dialect.name == 'postgresql':
        with engine.begin() as connection:
            connection.execute(text('CREATE INDEX IF NOT EXISTS chunk_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)'))


def get_db():
    with SessionLocal() as session:
        yield session
