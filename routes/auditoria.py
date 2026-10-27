import csv
import io
from flask import Blueprint, render_template, session, redirect, url_for, flash, Response, request
from database.db import get_connection
from routes.auth import login_required

auditoria_bp = Blueprint("auditoria", __name__)

def checar_permissao():
    if session.get("usuario_nivel") != "ADM" and "auditoria_visualizar" not in session.get("usuario_permissoes", ""):
        flash("Acesso negado. Você não tem permissão para ver a auditoria.", "error")
        return False
    return True

@auditoria_bp.route("/auditoria")
@login_required
def index():
    if not checar_permissao():
        return redirect(url_for("dashboard.index"))

    # Pega os filtros da URL (se existirem)
    filtro_data_inicio = request.args.get("data_inicio", "")
    filtro_data_fim = request.args.get("data_fim", "")
    filtro_usuario = request.args.get("usuario", "")
    filtro_acao = request.args.get("acao", "")

    conn = get_connection()
    
    query = "SELECT * FROM logs_auditoria WHERE 1=1"
    params = []

    if filtro_data_inicio:
        query += " AND date(data_hora) >= date(?)"
        params.append(filtro_data_inicio)

    if filtro_data_fim:
        query += " AND date(data_hora) <= date(?)"
        params.append(filtro_data_fim)

    if filtro_usuario:
        query += " AND username LIKE ?"
        params.append(f"%{filtro_usuario}%")

    if filtro_acao:
        query += " AND operacao = ?"
        params.append(filtro_acao)

    query += " ORDER BY id DESC LIMIT 500" # Limita a 500 para não travar a tela
    
    logs = conn.execute(query, params).fetchall()
    
    # Busca a lista de usuários únicos para o dropdown do filtro
    usuarios_db = conn.execute("SELECT DISTINCT username FROM logs_auditoria").fetchall()
    conn.close()

    return render_template(
        "auditoria.html", 
        logs=logs, 
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim,
        filtro_usuario=filtro_usuario,
        filtro_acao=filtro_acao,
        usuarios_db=usuarios_db
    )

@auditoria_bp.route("/auditoria/excel")
@login_required
def exportar_excel():
    if not checar_permissao():
        return redirect(url_for("dashboard.index"))

    # Aplica os mesmos filtros da tela no Excel
    filtro_data_inicio = request.args.get("data_inicio", "")
    filtro_data_fim = request.args.get("data_fim", "")
    filtro_usuario = request.args.get("usuario", "")
    filtro_acao = request.args.get("acao", "")

    conn = get_connection()
    
    query = "SELECT data_hora, username, operacao, valor_novo, ip FROM logs_auditoria WHERE 1=1"
    params = []

    if filtro_data_inicio:
        query += " AND date(data_hora) >= date(?)"
        params.append(filtro_data_inicio)
    if filtro_data_fim:
        query += " AND date(data_hora) <= date(?)"
        params.append(filtro_data_fim)
    if filtro_usuario:
        query += " AND username LIKE ?"
        params.append(f"%{filtro_usuario}%")
    if filtro_acao:
        query += " AND operacao = ?"
        params.append(filtro_acao)

    query += " ORDER BY id DESC"
    
    logs = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff') # BOM para o Excel reconhecer acentos
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow(["Data/Hora", "Usuário", "Ação", "Detalhes", "IP"])
    for log in logs:
        writer.writerow([log['data_hora'], log['username'], log['operacao'], log['valor_novo'], log['ip']])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=auditoria.csv"}
    )

@auditoria_bp.route("/auditoria/pdf")
@login_required
def imprimir_pdf():
    if not checar_permissao():
        return redirect(url_for("dashboard.index"))

    # Aplica os filtros no PDF também
    filtro_data_inicio = request.args.get("data_inicio", "")
    filtro_data_fim = request.args.get("data_fim", "")
    filtro_usuario = request.args.get("usuario", "")
    filtro_acao = request.args.get("acao", "")

    conn = get_connection()
    query = "SELECT * FROM logs_auditoria WHERE 1=1"
    params = []

    if filtro_data_inicio:
        query += " AND date(data_hora) >= date(?)"
        params.append(filtro_data_inicio)
    if filtro_data_fim:
        query += " AND date(data_hora) <= date(?)"
        params.append(filtro_data_fim)
    if filtro_usuario:
        query += " AND username LIKE ?"
        params.append(f"%{filtro_usuario}%")
    if filtro_acao:
        query += " AND operacao = ?"
        params.append(filtro_acao)

    query += " ORDER BY id DESC"
    
    logs = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("auditoria_pdf.html", logs=logs)