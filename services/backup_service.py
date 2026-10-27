"""
Backup protegido do banco SQLite com hash SHA-256 para verificação de integridade.
"""
import hashlib
import shutil
import datetime
import sqlite3
from pathlib import Path
from config import Config


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(8192), b""):
            h.update(bloco)
    return h.hexdigest()


def criar_backup() -> dict:
    """Cria cópia do banco + arquivo .sha256 com o hash."""
    src = Path(Config.DATABASE_PATH)
    if not src.exists():
        raise FileNotFoundError("Banco não encontrado.")

    # Backup consistente usando API do SQLite (lida com WAL/journal)
    Config.BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = Config.BACKUP_FOLDER / f"acessos_backup_{ts}.db"

    origem = sqlite3.connect(src)
    destino = sqlite3.connect(dst)
    try:
        origem.backup(destino)
    finally:
        destino.close()
        origem.close()

    digest = _sha256(dst)
    (dst.with_suffix(".db.sha256")).write_text(digest)

    return {"arquivo": str(dst), "sha256": digest,
            "tamanho": dst.stat().st_size}


def verificar_backup(caminho: str) -> dict:
    """Compara o hash do arquivo com o .sha256 ao lado."""
    p = Path(caminho)
    if not p.exists():
        return {"ok": False, "erro": "Arquivo não encontrado."}
    hash_file = p.with_suffix(".db.sha256")
    if not hash_file.exists():
        return {"ok": False, "erro": "Hash de verificação ausente."}
    esperado = hash_file.read_text().strip()
    atual = _sha256(p)
    return {"ok": esperado == atual, "esperado": esperado, "atual": atual}


def restaurar_backup(caminho: str) -> dict:
    """Restaura banco após verificação de integridade."""
    v = verificar_backup(caminho)
    if not v["ok"]:
        return {"ok": False, "erro": f"Falha de integridade: {v}"}
    # Backup do banco atual antes de sobrescrever
    atual = Path(Config.DATABASE_PATH)
    if atual.exists():
        shutil.copy2(atual, atual.with_suffix(".before_restore.db"))
    shutil.copy2(caminho, atual)
    return {"ok": True, "arquivo": str(atual)}