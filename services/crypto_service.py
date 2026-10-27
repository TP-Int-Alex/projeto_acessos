import os
from cryptography.fernet import Fernet
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from config import Config

_ph = PasswordHasher()
_fernet = None

def _load_or_create_key() -> bytes:
    key_file = Config.KEY_FILE
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_bytes()
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    try:
        os.chmod(key_file, 0o600)
    except Exception:
        pass
    return key

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet

def hash_password(password: str) -> str:
    return _ph.hash(password)

def verify_password(hash_str: str, password: str) -> bool:
    try:
        return _ph.verify(hash_str, password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False

def encrypt_secret(plaintext: str) -> bytes:
    if plaintext is None:
        return None
    return get_fernet().encrypt(plaintext.encode("utf-8"))

def decrypt_secret(ciphertext: bytes) -> str:
    if not ciphertext:
        return ""
    try:
        return get_fernet().decrypt(ciphertext).decode("utf-8")
    except Exception:
        return "<erro ao descriptografar>"