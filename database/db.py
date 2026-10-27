import sqlite3
from pathlib import Path
from config import Config

def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER',
    email TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    permissoes TEXT DEFAULT '',
    tentativas_login INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS ambientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_empresa TEXT NOT NULL,
    nome_identificacao TEXT,
    imagem_path TEXT,
    tipo_cliente TEXT DEFAULT 'LOCAL',
    versao_protheus TEXT, -- NOVA COLUNA AQUI
    portal_url TEXT,
    portal_login TEXT,
    portal_senha TEXT,
    responsavel_cadastro INTEGER,
    observacoes TEXT,
    status TEXT NOT NULL DEFAULT 'ativo',
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT,
    FOREIGN KEY (responsavel_cadastro) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS acessos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    ambiente_id INTEGER NOT NULL,
    sistema_servico TEXT,
    usuario_login TEXT,
    senha_cripto BLOB,
    endereco TEXT,
    porta TEXT,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    FOREIGN KEY (ambiente_id) REFERENCES ambientes(id)
);

CREATE TABLE IF NOT EXISTS logs_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    username TEXT,
    data_hora TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    operacao TEXT NOT NULL,
    entidade TEXT,
    entidade_id INTEGER,
    campo_alterado TEXT,
    valor_anterior TEXT,
    valor_novo TEXT,
    resultado TEXT,
    sessao_id TEXT,
    ip TEXT
);
"""

def init_db():
    Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript(SCHEMA)
    
    # Tenta adicionar colunas novas caso o banco já exista (evita erros de atualização)
    colunas_novas = [
        ("clientes", "tipo_cliente", "TEXT DEFAULT 'LOCAL'"),
        ("clientes", "versao_protheus", "TEXT"), # NOVA COLUNA AQUI
        ("clientes", "portal_url", "TEXT"),
        ("clientes", "portal_login", "TEXT"),
        ("clientes", "portal_senha", "TEXT"),
        ("clientes", "status", "TEXT DEFAULT 'ativo'"),
        ("usuarios", "permissoes", "TEXT DEFAULT ''")
    ]
    
    for tabela, coluna, tipo in colunas_novas:
        try:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass
            
    conn.execute("INSERT OR IGNORE INTO ambientes (nome, descricao) VALUES ('T-CLOUD', 'Ambiente TOTVS')")
    conn.execute("INSERT OR IGNORE INTO ambientes (nome, descricao) VALUES ('LOCAL', 'Ambiente Local')")
    conn.commit()
    conn.close()