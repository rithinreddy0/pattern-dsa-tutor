"""Resumable indexing: one embedding per problem, shared across its response modes."""
import time
from collections import defaultdict
from sqlalchemy import select
from fastapi import HTTPException
from .database import init_db, SessionLocal
from .models import Chunk, Problem
from .config import get_settings
from .seed import seed
from .rag import embed


def main(stop_event=None):
    settings = get_settings()
    if not settings.gemini_api_key:
        raise SystemExit('Set GEMINI_API_KEY before indexing.')

    def pause(seconds):
        if stop_event is not None:
            return stop_event.wait(seconds)
        time.sleep(seconds)
        return False

    init_db()
    with SessionLocal() as db:
        seed(db)
        groups = defaultdict(list)
        for chunk in db.scalars(select(Chunk)).all():
            groups[chunk.problem_id].append(chunk)
        pending = [p for p in db.scalars(select(Problem)).all() if any(c.embedding is None or c.embedding_model != settings.embedding_model for c in groups[p.id])]
        for start in range(0, len(pending), 20):
            if stop_event is not None and stop_event.is_set():
                return
            batch = pending[start:start+20]
            texts = [p.title + chr(10) + f'Topic: {p.topic}; pattern: {p.subtopic} | {p.statement} | ' + ' '.join(p.hints) for p in batch]
            for attempt in range(6):
                try:
                    vectors = embed(texts)
                    break
                except HTTPException as error:
                    if attempt == 5 or error.status_code not in (429, 503):
                        raise
                    print(f'Embedding API limit/unavailability ({error.status_code}); retrying.', flush=True)
                    if pause(min(5 * 2**attempt, 60)):
                        return
            for problem, vector in zip(batch, vectors):
                for chunk in groups[problem.id]:
                    chunk.embedding = vector
                    chunk.embedding_model = settings.embedding_model
            db.commit()
            print(f'Indexed {min(start+20, len(pending))}/{len(pending)} problems', flush=True)
            if pause(1):
                return
        print('Knowledge index is ready.', flush=True)


if __name__ == '__main__':
    main()
