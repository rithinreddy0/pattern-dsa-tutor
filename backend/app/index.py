"""Run: python -m app.index (resumable; only embeds missing/current-model chunks)."""
import time
from sqlalchemy import select, or_
from .database import init_db, SessionLocal
from .models import Chunk
from .config import get_settings
from .seed import seed
from .rag import embed
from fastapi import HTTPException


def main():
    settings = get_settings()
    if not settings.gemini_api_key:
        raise SystemExit('Set GEMINI_API_KEY before indexing.')
    init_db()
    with SessionLocal() as db:
        seed(db)
        chunks = db.scalars(select(Chunk).where(or_(Chunk.embedding.is_(None), Chunk.embedding_model.is_(None), Chunk.embedding_model != settings.embedding_model))).all()
        for start in range(0, len(chunks), 20):
            batch = chunks[start:start+20]
            for attempt in range(6):
                try:
                    vectors = embed([c.content for c in batch])
                    break
                except HTTPException:
                    if attempt == 5:
                        raise
                    print('Embedding request unavailable; waiting before retry.', flush=True)
                    time.sleep(min(5 * 2**attempt, 60))
            for chunk, vector in zip(batch, vectors):
                chunk.embedding = vector
                chunk.embedding_model = settings.embedding_model
            db.commit()
            print(f'Indexed {min(start+20, len(chunks))}/{len(chunks)} chunks', flush=True)
            time.sleep(1)
        print('Knowledge index is ready.')


if __name__ == '__main__':
    main()
