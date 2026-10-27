from flask import Blueprint, render_template, session
from database.db import get_connection
from routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    conn = get_connection()
    
    # Contadores Básicos
    total_clientes = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_acessos = conn.execute("SELECT COUNT(*) FROM acessos").fetchone()[0]
    total_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    
    # Contadores de Status de Clientes
    clientes_ativos = conn.execute("SELECT COUNT(*) FROM clientes WHERE status = 'ativo' OR status IS NULL").fetchone()[0]
    clientes_inativos = conn.execute("SELECT COUNT(*) FROM clientes WHERE status = 'inativo'").fetchone()[0]
    
    # Contadores por Tipo de Cliente
    clientes_local = conn.execute("SELECT COUNT(*) FROM clientes WHERE tipo_cliente = 'LOCAL'").fetchone()[0]
    clientes_tcloud = conn.execute("SELECT COUNT(*) FROM clientes WHERE tipo_cliente = 'T-CLOUD'").fetchone()[0]
    
    # Contador por Versão do Protheus
    versoes = conn.execute("""
        SELECT versao_protheus, COUNT(*) as qtd 
        FROM clientes 
        WHERE versao_protheus IS NOT NULL AND versao_protheus != ''
        GROUP BY versao_protheus 
        ORDER BY qtd DESC LIMIT 5
    """).fetchall()
    
    # Últimos 5 logs
    try:
        ultimos_logs = conn.execute("SELECT username, operacao, data_hora FROM logs_auditoria ORDER BY id DESC LIMIT 5").fetchall()
    except Exception:
        ultimos_logs = []
        
    conn.close()

    # Evitar divisão por zero nos gráficos percentuais
    def calc_porcentagem(valor, total):
        return (valor / total * 100) if total > 0 else 0

    dados_graficos = {
        "pct_ativos": calc_porcentagem(clientes_ativos, total_clientes),
        "pct_inativos": calc_porcentagem(clientes_inativos, total_clientes),
        "pct_local": calc_porcentagem(clientes_local, total_clientes),
        "pct_tcloud": calc_porcentagem(clientes_tcloud, total_clientes),
        "versoes": versoes,
        "max_versao": max([v['qtd'] for v in versoes]) if versoes else 1
    }

    nome_usuario = session.get("usuario_nome", "Usuário")
    nivel_usuario = session.get("usuario_nivel", "USER")

    return render_template(
        "dashboard.html", 
        total_clientes=total_clientes,
        total_acessos=total_acessos,
        total_usuarios=total_usuarios,
        clientes_ativos=clientes_ativos,
        clientes_inativos=clientes_inativos,
        clientes_local=clientes_local,
        clientes_tcloud=clientes_tcloud,
        ultimos_logs=ultimos_logs,
        nome_usuario=nome_usuario,
        nivel_usuario=nivel_usuario,
        dados_graficos=dados_graficos
    )