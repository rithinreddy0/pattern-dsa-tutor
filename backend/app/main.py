from contextlib import asynccontextmanager
from collections import Counter
from typing import Literal
import json
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, delete, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import get_settings
from .database import init_db, get_db, SessionLocal, engine
from .models import User, Problem, Bookmark, Progress, Conversation, Message, Chunk
from .security import current_user, issue_token, password_hasher, _dummy_hash, rate_limit
from .seed import seed, DATA
from .rag import answer, retrieve
from pathlib import Path
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app):
    init_db()
    if get_settings().auto_seed:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title='Pattern DSA Tutor', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().origins, allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


@app.middleware('http')
async def security_headers(request: Request, call_next):
    if int(request.headers.get('content-length', '0') or 0) > 24000:
        from starlette.responses import JSONResponse
        return JSONResponse({'detail': 'Request is too large.'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


class Register(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    mode: Literal['hint', 'explanation', 'solution'] = 'hint'
    problem_id: str | None = Field(default=None, max_length=90)
    conversation_id: str | None = Field(default=None, max_length=36)


class ProgressRequest(BaseModel):
    status: Literal['not_started', 'in_progress', 'solved']


class PreviewHistoryEntry(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=1500)
    mode: Literal['hint', 'explanation', 'solution'] = 'hint'


class PreviewChatRequest(ChatRequest):
    history: list[PreviewHistoryEntry] = Field(default_factory=list, max_length=6)


def public_user(user):
    return {'id': user.id, 'name': user.name, 'email': user.email}


def summary(p):
    return {k: getattr(p, k) for k in ['id', 'title', 'topic', 'subtopic', 'difficulty', 'tags', 'source_url', 'source_name', 'license']}


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    settings = get_settings()
    indexed = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.embedding_model == settings.embedding_model)) or 0
    return {'status': 'ok', 'ai': 'gemini' if settings.gemini_api_key else 'local', 'retrieval': 'pgvector' if engine.dialect.name == 'postgresql' and settings.gemini_api_key and indexed else 'lexical', 'indexed_chunks': indexed, 'database': engine.dialect.name}


@app.post('/api/auth/register', status_code=201)
def register(data: Register, request: Request, db: Session = Depends(get_db)):
    rate_limit(f'auth:{request.client.host}', 12, 300)
    user = User(name=data.name.strip() or 'Learner', email=str(data.email).lower(), password_hash=password_hasher.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account with that email already exists.')
    return {'user': public_user(user), 'access_token': issue_token(user), 'token_type': 'bearer'}


@app.post('/api/auth/login')
def login(data: Login, request: Request, db: Session = Depends(get_db)):
    rate_limit(f'auth:{request.client.host}', 12, 300)
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = password_hasher.verify(data.password, user.password_hash if user else _dummy_hash)
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    return {'user': public_user(user), 'access_token': issue_token(user), 'token_type': 'bearer'}


@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return public_user(user)


@app.get('/api/topics')
def topics(db: Session = Depends(get_db)):
    taxonomy = json.loads((DATA / 'taxonomy.json').read_text(encoding='utf-8'))
    counts = dict(db.execute(select(Problem.topic, func.count()).group_by(Problem.topic)).all())
    for topic in taxonomy:
        topic['count'] = counts.get(topic['name'], 0)
    return taxonomy


@app.get('/api/problems')
def problems(q: str = Query('', max_length=300), topic: str = '', subtopic: str = '', difficulty: str = '', page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    statement = select(Problem)
    if q.strip():
        # Literal substring search: escape SQL LIKE wildcard characters.
        pattern = '%' + q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        statement = statement.where((Problem.title.ilike(pattern, escape='\\')) | (Problem.statement.ilike(pattern, escape='\\')))
    if topic:
        statement = statement.where(Problem.topic == topic)
    if subtopic:
        statement = statement.where(Problem.subtopic == subtopic)
    if difficulty:
        statement = statement.where(Problem.difficulty == difficulty)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    items = db.scalars(statement.order_by(Problem.title).offset((page-1)*page_size).limit(page_size)).all()
    return {'items': [summary(p) for p in items], 'total': total, 'page': page, 'page_size': page_size}


@app.get('/api/problems/{problem_id}')
def problem(problem_id: str, db: Session = Depends(get_db)):
    p = db.get(Problem, problem_id)
    if not p:
        raise HTTPException(404, 'Problem not found')
    return {**summary(p), **{k: getattr(p, k) for k in ['statement', 'hints', 'explanation', 'solution', 'language', 'time_complexity', 'space_complexity']}}


@app.get('/api/search')
def semantic_search(request: Request, q: str = Query(min_length=2, max_length=500), db: Session = Depends(get_db)):
    rate_limit(f'search:{request.client.host}', 20)
    rows, method = retrieve(db, q, limit=30)
    found = {}
    for chunk, score in rows:
        if method == 'lexical' and score <= 0.02:
            continue
        if chunk.problem_id not in found:
            found[chunk.problem_id] = {**summary(db.get(Problem, chunk.problem_id)), 'score': round(score, 3)}
    return {'items': list(found.values())[:10], 'retrieval': method}


def owned_conversation(db, conversation_id, user):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(404, 'Conversation not found')
    return conversation


@app.post('/api/chat/preview')
def preview_chat(data: PreviewChatRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(f'preview:{request.client.host}', 8)
    return answer(db, data.question, data.mode, data.problem_id, data.history)


@app.post('/api/chat')
def chat(data: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(f'chat:{user.id}', 20)
    history = []
    conversation = None
    if data.conversation_id:
        conversation = owned_conversation(db, data.conversation_id, user)
        history = list(reversed(db.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc()).limit(6)).all()))
    pid = conversation.problem_id if conversation else data.problem_id
    result = answer(db, data.question, data.mode, pid, history)
    if not conversation:
        conversation = Conversation(user_id=user.id, title=data.question[:100], problem_id=pid)
        db.add(conversation)
        db.flush()
    db.add(Message(conversation_id=conversation.id, role='user', content=data.question, mode=data.mode))
    db.add(Message(conversation_id=conversation.id, role='assistant', content=result['content'], mode=data.mode, citations=result['citations'], provider=result['provider']))
    db.commit()
    return {**result, 'conversation_id': conversation.id}


@app.get('/api/conversations')
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{'id': c.id, 'title': c.title, 'problem_id': c.problem_id, 'created_at': c.created_at} for c in db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at.desc()).limit(100))]


@app.get('/api/conversations/{conversation_id}')
def conversation_detail(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = owned_conversation(db, conversation_id, user)
    messages = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at, Message.id)).all()
    return {'id': c.id, 'title': c.title, 'problem_id': c.problem_id, 'messages': [{k: getattr(m, k) for k in ['id', 'role', 'content', 'mode', 'citations', 'provider', 'created_at']} for m in messages]}


@app.delete('/api/conversations/{conversation_id}', status_code=204)
def delete_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = owned_conversation(db, conversation_id, user)
    db.delete(c)
    db.commit()


@app.get('/api/me/learning')
def learning(user: User = Depends(current_user), db: Session = Depends(get_db)):
    bookmarks = db.scalars(select(Bookmark.problem_id).where(Bookmark.user_id == user.id)).all()
    progress = db.scalars(select(Progress).where(Progress.user_id == user.id)).all()
    return {'bookmarks': list(bookmarks), 'progress': {p.problem_id: p.status for p in progress}}


@app.put('/api/me/bookmarks/{problem_id}')
def bookmark(problem_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Problem, problem_id):
        raise HTTPException(404, 'Problem not found')
    if not db.get(Bookmark, (user.id, problem_id)):
        db.add(Bookmark(user_id=user.id, problem_id=problem_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {'bookmarked': True}


@app.delete('/api/me/bookmarks/{problem_id}', status_code=204)
def unbookmark(problem_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(Bookmark).where(Bookmark.user_id == user.id, Bookmark.problem_id == problem_id))
    db.commit()


@app.put('/api/me/progress/{problem_id}')
def update_progress(problem_id: str, data: ProgressRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Problem, problem_id):
        raise HTTPException(404, 'Problem not found')
    progress = db.get(Progress, (user.id, problem_id))
    if not progress:
        progress = Progress(user_id=user.id, problem_id=problem_id)
        db.add(progress)
    progress.status = data.status
    db.commit()
    return {'status': progress.status}


@app.get('/api/sources')
def sources():
    return json.loads((DATA / 'sources.json').read_text(encoding='utf-8'))


# A combined Render deployment can serve the built React app from the same origin.
# API routes above take precedence. Vercel/local Vite deployments still work separately.
frontend_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='frontend')
