from database.db import get_connection

def registrar(usuario_id, username, operacao, entidade=None, entidade_id=None,
              campo=None, valor_anterior=None, valor_novo=None,
              resultado="sucesso", sessao_id=None, ip=None):
    # Nunca logar senhas em texto puro
    def safe(v):
        if v is None:
            return None
        s = str(v)
        if len(s) > 500:
            s = s[:500] + "..."
        return s

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO logs_auditoria
            (usuario_id, username, operacao, entidade, entidade_id,
             campo_alterado, valor_anterior, valor_novo, resultado, sessao_id, ip)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (usuario_id, username, operacao, entidade, entidade_id,
              campo, safe(valor_anterior), safe(valor_novo), resultado, sessao_id, ip))
        conn.commit()
    finally:
        conn.close()