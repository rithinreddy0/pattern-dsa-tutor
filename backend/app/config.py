from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets
import sys


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    environment: str = 'development'
    database_url: str = 'sqlite:///./tutor.db'
    jwt_secret: str = ''
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    gemini_api_key: str = ''
    use_os_keyring: bool = True
    gemini_model: str = 'gemini-2.5-flash'
    embedding_model: str = 'gemini-embedding-2'
    auto_seed: bool = True
    auto_index: bool = False
    token_expire_minutes: int = 480

    @property
    def origins(self):
        return [x.strip().rstrip('/') for x in self.cors_origins.split(',') if x.strip()]


@lru_cache
def get_settings():
    settings = Settings()
    if not settings.gemini_api_key and settings.use_os_keyring and sys.platform == 'win32':
        try:
            import keyring
            settings.gemini_api_key = keyring.get_password('pattern-dsa-tutor', 'gemini-api-key') or ''
        except (ImportError, RuntimeError):
            pass
    if settings.environment == 'production':
        if len(settings.jwt_secret) < 32:
            raise RuntimeError('Production requires JWT_SECRET with at least 32 characters')
        if not settings.database_url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
            raise RuntimeError('Production requires a persistent PostgreSQL DATABASE_URL')
        if not settings.gemini_api_key:
            raise RuntimeError('Production requires GEMINI_API_KEY')
        if not settings.origins or '*' in settings.origins or any(not x.startswith('https://') for x in settings.origins):
            raise RuntimeError('Production requires explicit HTTPS CORS_ORIGINS')
    if not settings.jwt_secret:
        # Development sessions expire on restart; never ship a shared default secret.
        settings.jwt_secret = secrets.token_urlsafe(48)
    return settings
