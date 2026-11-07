import json
from pathlib import Path
from sqlalchemy import select
from .models import Problem, Chunk

DATA = Path(__file__).resolve().parent.parent / 'data'


def seed(db):
    path = DATA / 'problems.json'
    if not path.exists():
        return
    existing = set(db.scalars(select(Problem.id)).all())
    for item in json.loads(path.read_text(encoding='utf-8')):
        if item['id'] in existing:
            continue
        problem = Problem(**item)
        db.add(problem)
        db.flush()
        # Hint chunks never contain the full solution. Modes retrieve separate content.
        sections = {
            'hint': '\n'.join(item['hints']),
            'explanation': item['explanation'],
            'solution': item['solution'],
        }
        for kind, content in sections.items():
            prefix = f"{item['title']} | {item['topic']} | {item['subtopic']}\n{item['statement']}\n"
            for index, start in enumerate(range(0, max(1, len(content)), 4000)):
                db.add(Chunk(id=f"{item['id']}:{kind}:{index}", problem_id=problem.id, kind=kind, content=prefix + content[start:start + 4400]))
    db.commit()
