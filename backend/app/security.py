from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import threading
import time
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
_dummy_hash = password_hasher.hash('dummy-password-for-constant-time-verification')
_buckets = defaultdict(deque)
_lock = threading.Lock()


def rate_limit(key: str, limit: int, seconds: int = 60):
    with _lock:
        current = time.monotonic()
        bucket = _buckets[key]
        while bucket and bucket[0] < current - seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(429, 'Too many requests. Please try again shortly.', headers={'Retry-After': str(seconds)})
        bucket.append(current)
        if len(_buckets) > 10000:
            stale = [k for k, v in _buckets.items() if not v or v[-1] < current - 3600]
            for k in stale:
                del _buckets[k]


def issue_token(user: User):
    settings = get_settings()
    current = datetime.now(timezone.utc)
    return jwt.encode({'sub': user.id, 'iat': current, 'exp': current + timedelta(minutes=settings.token_expire_minutes), 'iss': 'pattern-dsa'}, settings.jwt_secret, algorithm='HS256')


def current_user(auth: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if auth is None:
        raise HTTPException(401, 'Please sign in to save your learning progress.')
    try:
        payload = jwt.decode(auth.credentials, get_settings().jwt_secret, algorithms=['HS256'], issuer='pattern-dsa', options={'require': ['exp', 'sub', 'iat']})
        user = db.get(User, payload['sub'])
        if user is None:
            raise ValueError('Unknown user')
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Your session has expired. Please sign in again.')
