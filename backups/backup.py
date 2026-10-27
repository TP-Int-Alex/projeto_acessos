"""
Rotina de backup manual do banco SQLite.
Uso: python backups/backup.py
"""
import shutil, datetime, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import Config

def backup():
    src = Config.DATABASE_PATH
    if not src.exists():
        print("Banco não encontrado."); return
    Config.BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = Config.BACKUP_FOLDER / f"acessos_backup_{ts}.db"
    shutil.copy2(src, dst)
    print(f"Backup criado: {dst}")

def restaurar(arquivo):
    src = Path(arquivo)
    if not src.exists():
        print("Arquivo de backup não encontrado."); return
    shutil.copy2(src, Config.DATABASE_PATH)
    print("Banco restaurado com sucesso.")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "restore":
        restaurar(sys.argv[2])
    else:
        backup()