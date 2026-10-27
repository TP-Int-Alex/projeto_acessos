from datetime import datetime, timedelta
from database.db import get_connection
from services.crypto_service import hash_password, verify_password
from config import Config

def criar_usuario_inicial(username, password, role):
    conn = get_connection()
    try:
        cur = conn.execute("SELECT id FROM usuarios WHERE username=?", (username,))
        if cur.fetchone():
            return
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, role, ativo) VALUES (?,?,?,1)",
            (username, hash_password(password), role)
        )
        conn.commit()
    finally:
        conn.close()

def autenticar(username, password):
    conn = get_connection()
    try:
        u = conn.execute("SELECT * FROM usuarios WHERE username=?", (username,)).fetchone()
        if not u:
            return None, "Usuário ou senha inválidos."
        if not u["ativo"]:
            return None, "Conta desativada."
        if u["bloqueado_ate"]:
            try:
                bloqueio = datetime.fromisoformat(u["bloqueado_ate"])
                if bloqueio > datetime.now():
                    restante = int((bloqueio - datetime.now()).total_seconds() / 60) + 1
                    return None, f"Conta bloqueada. Tente novamente em {restante} min."
            except Exception:
                pass
        if verify_password(u["password_hash"], password):
            conn.execute("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=NULL WHERE id=?", (u["id"],))
            conn.commit()
            return dict(u), None
        # Falha: incrementar tentativas
        tent = (u["tentativas_login"] or 0) + 1
        bloqueio_ate = None
        if tent >= Config.MAX_LOGIN_ATTEMPTS:
            bloqueio_ate = (datetime.now() + timedelta(minutes=Config.LOGIN_BLOCK_MINUTES)).isoformat()
            tent = 0
        conn.execute("UPDATE usuarios SET tentativas_login=?, bloqueado_ate=? WHERE id=?",
                     (tent, bloqueio_ate, u["id"]))
        conn.commit()
        return None, "Usuário ou senha inválidos."
    finally:
        conn.close()