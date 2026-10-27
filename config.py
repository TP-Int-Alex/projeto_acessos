import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    DATABASE_PATH = BASE_DIR / "database" / "acessos.db"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    BACKUP_FOLDER = BASE_DIR / "backups"
    KEY_FILE = BASE_DIR / "database" / "secret.key"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_BLOCK_MINUTES = 15
    POR_PAGINA = 9
    POR_PAGINA_COFRE = 12