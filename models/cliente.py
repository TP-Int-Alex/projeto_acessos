from database.db import get_connection
from math import ceil

POR_PAGINA = 9


def listar(busca=None, ambiente=None, status=None, pagina=1, por_pagina=POR_PAGINA):
    conn = get_connection()
    where, params = "WHERE 1=1", []

    if busca:
        where += " AND (c.nome_empresa LIKE ? OR c.nome_identificacao LIKE ?)"
        params += [f"%{busca}%", f"%{busca}%"]
    if status:
        where += " AND c.status=?"
        params.append(status)
    if ambiente:
        where += (" AND EXISTS (SELECT 1 FROM acessos a JOIN ambientes am "
                  "ON a.ambiente_id=am.id WHERE a.cliente_id=c.id AND am.nome=?)")
        params.append(ambiente)

    total = conn.execute(f"SELECT COUNT(*) c FROM clientes c {where}", params).fetchone()["c"]
    total_paginas = max(1, ceil(total / por_pagina))
    pagina = max(1, min(pagina, total_paginas))

    sql = f"""
        SELECT c.*,
               (SELECT COUNT(*) FROM acessos a WHERE a.cliente_id=c.id) AS total_acessos,
               (SELECT GROUP_CONCAT(DISTINCT am.nome) FROM acessos a
                JOIN ambientes am ON a.ambiente_id=am.id WHERE a.cliente_id=c.id) AS ambientes
        FROM clientes c {where}
        ORDER BY c.criado_em DESC
        LIMIT ? OFFSET ?
    """
    params_pag = params + [por_pagina, (pagina - 1) * por_pagina]
    rows = conn.execute(sql, params_pag).fetchall()
    conn.close()
    return {
        "itens": [dict(r) for r in rows],
        "total": total, "pagina": pagina,
        "total_paginas": total_paginas, "por_pagina": por_pagina,
    }


def obter(cliente_id):
    conn = get_connection()
    c = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    if not c:
        conn.close(); return None
    acessos = conn.execute("""
        SELECT a.*, am.nome AS ambiente_nome
        FROM acessos a JOIN ambientes am ON a.ambiente_id=am.id
        WHERE a.cliente_id=? ORDER BY a.id DESC
    """, (cliente_id,)).fetchall()
    conn.close()
    return {"cliente": dict(c), "acessos": [dict(a) for a in acessos]}


def criar(dados, usuario_id):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO clientes (nome_empresa, nome_identificacao, imagem_path,
                              responsavel_cadastro, observacoes, status)
        VALUES (?,?,?,?,?,?)
    """, (dados["nome_empresa"], dados.get("nome_identificacao"),
          dados.get("imagem_path"), usuario_id,
          dados.get("observacoes"), dados.get("status", "ativo")))
    cid = cur.lastrowid
    conn.commit(); conn.close()
    return cid


def atualizar(cliente_id, dados):
    conn = get_connection()
    conn.execute("""
        UPDATE clientes SET nome_empresa=?, nome_identificacao=?, imagem_path=?,
            observacoes=?, status=?, atualizado_em=datetime('now','localtime')
        WHERE id=?
    """, (dados["nome_empresa"], dados.get("nome_identificacao"),
          dados.get("imagem_path"), dados.get("observacoes"),
          dados.get("status", "ativo"), cliente_id))
    conn.commit(); conn.close()


def arquivar(cliente_id):
    """Arquivamento lógico — preserva dados, apenas marca inativo."""
    conn = get_connection()
    conn.execute("""
        UPDATE clientes SET status='inativo',
            atualizado_em=datetime('now','localtime') WHERE id=?
    """, (cliente_id,))
    conn.commit(); conn.close()


def excluir(cliente_id):
    conn = get_connection()
    conn.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    conn.commit(); conn.close()


def estatisticas():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"]
    tcloud = conn.execute("""SELECT COUNT(*) c FROM acessos a
                             JOIN ambientes am ON a.ambiente_id=am.id
                             WHERE am.nome='T-CLOUD'""").fetchone()["c"]
    interno = conn.execute("""SELECT COUNT(*) c FROM acessos a
                              JOIN ambientes am ON a.ambiente_id=am.id
                              WHERE am.nome='INTERNO'""").fetchone()["c"]
    ativos = conn.execute("SELECT COUNT(*) c FROM clientes WHERE status='ativo'").fetchone()["c"]
    inativos = conn.execute("SELECT COUNT(*) c FROM clientes WHERE status='inativo'").fetchone()["c"]
    total_acessos = conn.execute("SELECT COUNT(*) c FROM acessos").fetchone()["c"]

    ultimos = conn.execute("SELECT nome_empresa, criado_em FROM clientes ORDER BY criado_em DESC LIMIT 5").fetchall()

    # série dos últimos 6 meses (para gráfico)
    serie = conn.execute("""
        SELECT strftime('%Y-%m', criado_em) AS mes, COUNT(*) AS total
        FROM clientes
        WHERE criado_em >= date('now','-6 months')
        GROUP BY mes ORDER BY mes
    """).fetchall()

    por_ambiente = conn.execute("""
        SELECT am.nome AS ambiente, COUNT(*) AS total
        FROM acessos a JOIN ambientes am ON a.ambiente_id = am.id
        GROUP BY am.nome
    """).fetchall()

    conn.close()
    return {
        "total_clientes": total, "total_tcloud": tcloud, "total_interno": interno,
        "ativos": ativos, "inativos": inativos, "total_acessos": total_acessos,
        "ultimos_clientes": [dict(r) for r in ultimos],
        "serie_mensal": [dict(r) for r in serie],
        "por_ambiente": [dict(r) for r in por_ambiente],
    }


def adicionar_acesso(cliente_id, dados):
    conn = get_connection()
    amb = conn.execute("SELECT id FROM ambientes WHERE nome=?", (dados["ambiente"],)).fetchone()
    if not amb:
        conn.close(); return None
    cur = conn.execute("""
        INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico,
            usuario_login, senha_cripto, endereco, porta, observacoes)
        VALUES (?,?,?,?,?,?,?,?)
    """, (cliente_id, amb["id"], dados.get("sistema_servico"),
          dados.get("usuario_login"), dados.get("senha_cripto"),
          dados.get("endereco"), dados.get("porta"), dados.get("observacoes")))
    aid = cur.lastrowid
    conn.commit(); conn.close()
    return aid


def obter_acesso(acesso_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT a.*, am.nome AS ambiente_nome, c.nome_empresa
        FROM acessos a
        JOIN ambientes am ON a.ambiente_id = am.id
        JOIN clientes c ON a.cliente_id = c.id
        WHERE a.id = ?
    """, (acesso_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def listar_cofre(busca=None, ambiente=None, pagina=1, por_pagina=12):
    """Lista todos os acessos (cofre global) com busca e filtro por ambiente."""
    conn = get_connection()
    where, params = "WHERE 1=1", []
    if busca:
        where += " AND (c.nome_empresa LIKE ? OR a.sistema_servico LIKE ? OR a.usuario_login LIKE ?)"
        params += [f"%{busca}%"] * 3
    if ambiente:
        where += " AND am.nome=?"
        params.append(ambiente)

    total = conn.execute(f"""
        SELECT COUNT(*) c FROM acessos a
        JOIN clientes c ON a.cliente_id=c.id
        JOIN ambientes am ON a.ambiente_id=am.id
        {where}
    """, params).fetchone()["c"]
    total_paginas = max(1, ceil(total / por_pagina))
    pagina = max(1, min(pagina, total_paginas))

    rows = conn.execute(f"""
        SELECT a.id, a.sistema_servico, a.usuario_login, a.endereco, a.porta,
               a.observacoes, a.criado_em, a.atualizado_em,
               am.nome AS ambiente_nome,
               c.nome_empresa, c.id AS cliente_id, c.imagem_path
        FROM acessos a
        JOIN clientes c ON a.cliente_id=c.id
        JOIN ambientes am ON a.ambiente_id=am.id
        {where}
        ORDER BY c.nome_empresa, am.nome
        LIMIT ? OFFSET ?
    """, params + [por_pagina, (pagina - 1) * por_pagina]).fetchall()
    conn.close()
    return {"itens": [dict(r) for r in rows], "total": total,
            "pagina": pagina, "total_paginas": total_paginas}