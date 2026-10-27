import os
import uuid
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, Response
from werkzeug.utils import secure_filename
from database.db import get_connection
from routes.auth import login_required

clientes_bp = Blueprint("clientes", __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def registrar_log(conn, operacao, entidade, entidade_id, detalhes=""):
    try:
        usuario_id = session.get("usuario_id")
        username = session.get("usuario_nome", "Sistema")
        ip = request.remote_addr or "127.0.0.1"
        conn.execute("""
            INSERT INTO logs_auditoria (usuario_id, username, operacao, entidade, entidade_id, valor_novo, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (usuario_id, username, operacao, entidade, entidade_id, detalhes, ip))
        conn.commit()
    except Exception as e:
        print(f"Erro ao gravar log: {e}")

@clientes_bp.route("/clientes", methods=["GET", "POST"])
@login_required
def index():
    conn = get_connection()
    
    if request.method == "POST":
        if session.get("usuario_nivel") != "ADM" and "clientes_criar" not in session.get("usuario_permissoes", ""):
            flash("Acesso negado para cadastrar clientes.", "error")
            return redirect(url_for("clientes.index"))

        # Forçando str() para o Pylance não reclamar
        nome_empresa = str(request.form.get("nome_empresa", ""))
        nome_identificacao = str(request.form.get("nome_identificacao", ""))
        tipo_cliente = str(request.form.get("tipo_cliente", ""))
        versao_protheus = str(request.form.get("versao_protheus", ""))
        observacoes = str(request.form.get("observacoes", ""))
        
        url_acesso = str(request.form.get("url_acesso", ""))
        login_acesso = str(request.form.get("login_acesso", ""))
        senha_acesso = str(request.form.get("senha_acesso", ""))
        
        protheus_login = str(request.form.get("protheus_login", ""))
        protheus_senha = str(request.form.get("protheus_senha", ""))
        
        db_login = str(request.form.get("db_login", ""))
        db_senha = str(request.form.get("db_senha", ""))

        anydesk_login = str(request.form.get("anydesk_login", ""))
        anydesk_senha = str(request.form.get("anydesk_senha", ""))
        
        windows_login = str(request.form.get("windows_login", ""))
        windows_senha = str(request.form.get("windows_senha", ""))
        
        portal_url = str(request.form.get("portal_url", ""))
        portal_login = str(request.form.get("portal_login", ""))
        portal_senha = str(request.form.get("portal_senha", ""))

        imagem_path = None
        file = request.files.get('imagem')
        
        # Trava de segurança para o Pylance
        if file and file.filename:
            filename_str = str(file.filename)
            if filename_str != '' and allowed_file(filename_str):
                filename = secure_filename(filename_str)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                imagem_path = unique_filename

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clientes (nome_empresa, nome_identificacao, imagem_path, tipo_cliente, versao_protheus, observacoes,
                                      portal_url, portal_login, portal_senha, responsavel_cadastro, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome_empresa, nome_identificacao, imagem_path, tipo_cliente, versao_protheus, observacoes,
                  portal_url, portal_login, portal_senha, 1, 'ativo'))
            
            cliente_id = cursor.lastrowid
            
            if url_acesso or login_acesso or senha_acesso:
                ambiente_nome = "T-CLOUD" if tipo_cliente == "T-CLOUD" else "LOCAL"
                ambiente = conn.execute("SELECT id FROM ambientes WHERE nome = ?", (ambiente_nome,)).fetchone()
                ambiente_id = ambiente["id"] if ambiente else 1
                cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                               (cliente_id, ambiente_id, "Acesso Principal", login_acesso, senha_acesso, url_acesso))

            if protheus_login or protheus_senha:
                cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                               (cliente_id, 1, "Protheus", protheus_login, protheus_senha, ""))

            if db_login or db_senha:
                cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                               (cliente_id, 1, "Banco de Dados", db_login, db_senha, ""))

            if anydesk_login or anydesk_senha:
                cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                               (cliente_id, 1, "AnyDesk", anydesk_login, anydesk_senha, ""))

            if windows_login or windows_senha:
                cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                               (cliente_id, 1, "Windows", windows_login, windows_senha, ""))

            conn.commit()
            registrar_log(conn, "CRIAR", "Cliente", cliente_id, f"Cadastrou o cliente {nome_empresa}")
            
            flash("Cliente cadastrado com sucesso!", "success")
            return redirect(url_for("clientes.index"))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar cliente: {str(e)}", "error")

    # --- FILTROS ---
    filtro_nome = str(request.args.get("nome", ""))
    filtro_tipo = str(request.args.get("tipo", ""))
    filtro_status = str(request.args.get("status", "todos"))
    filtro_versao = str(request.args.get("versao", ""))
    
    query = "SELECT * FROM clientes WHERE 1=1"
    params = []
    
    if filtro_nome:
        query += " AND (nome_empresa LIKE ? OR nome_identificacao LIKE ?)"
        params.append(f"%{filtro_nome}%")
        params.append(f"%{filtro_nome}%")

    if filtro_tipo:
        query += " AND tipo_cliente = ?"
        params.append(filtro_tipo)
    if filtro_status == "ativo":
        query += " AND (status = 'ativo' OR status IS NULL)"
    elif filtro_status == "inativo":
        query += " AND status = 'inativo'"
    if filtro_versao:
        query += " AND versao_protheus LIKE ?"
        params.append(f"%{filtro_versao}%")

    query += " ORDER BY nome_empresa"
    
    try:
        clientes = conn.execute(query, params).fetchall()
    except Exception:
        clientes = conn.execute("SELECT * FROM clientes").fetchall()
        
    conn.close()
    
    return render_template(
        "clientes.html", 
        clientes=clientes, 
        filtro_nome=filtro_nome, 
        filtro_tipo=filtro_tipo, 
        filtro_status=filtro_status, 
        filtro_versao=filtro_versao,
        filtro_data_inicio=str(request.args.get("data_inicio", "")),
        filtro_data_fim=str(request.args.get("data_fim", "")),
        filtro_ordem=str(request.args.get("ordem", "nome_empresa")),
        filtro_titulo=str(request.args.get("titulo", "Relatório de Clientes"))
    )

# --- ROTA: IMPRIMIR PDF ---
@clientes_bp.route("/clientes/imprimir")
@login_required
def imprimir():
    conn = get_connection()
    
    titulo = str(request.args.get("titulo", "Relatório de Clientes"))
    orientacao = str(request.args.get("orientacao", "portrait"))
    data_inicio = str(request.args.get("data_inicio", ""))
    data_fim = str(request.args.get("data_fim", ""))
    status = str(request.args.get("status", "todos"))
    tipo = str(request.args.get("tipo", ""))

    query = "SELECT * FROM clientes WHERE 1=1"
    params = []

    if data_inicio:
        query += " AND date(criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        query += " AND date(criado_em) <= date(?)"
        params.append(data_fim)
    if status == "ativo":
        query += " AND (status = 'ativo' OR status IS NULL)"
    elif status == "inativo":
        query += " AND status = 'inativo'"
    if tipo:
        query += " AND tipo_cliente = ?"
        params.append(tipo)

    query += " ORDER BY nome_empresa"
    clientes = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("clientes_imprimir.html", clientes=clientes, titulo=titulo, orientacao=orientacao)

# --- NOVA ROTA: EXPORTAR EXCEL (CSV) ---
@clientes_bp.route("/clientes/excel")
@login_required
def excel():
    conn = get_connection()
    tipo = str(request.args.get("tipo", ""))
    status = str(request.args.get("status", "todos"))

    query = "SELECT * FROM clientes WHERE 1=1"
    params = []

    if status == "ativo":
        query += " AND (status = 'ativo' OR status IS NULL)"
    elif status == "inativo":
        query += " AND status = 'inativo'"
    if tipo:
        query += " AND tipo_cliente = ?"
        params.append(tipo)

    query += " ORDER BY nome_empresa"
    clientes = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow(["Nome da Empresa", "Sigla", "Tipo", "Versão Protheus", "Status", "Data Cadastro"])
    
    for c in clientes:
        writer.writerow([
            c['nome_empresa'], 
            c['nome_identificacao'] or '', 
            c['tipo_cliente'] or 'LOCAL', 
            c['versao_protheus'] or '', 
            'Ativo' if c['status'] != 'inativo' else 'Inativo',
            c['criado_em'][:10] if c['criado_em'] else ''
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=relatorio_clientes.csv"}
    )

@clientes_bp.route("/clientes/visualizar/<int:id>")
@login_required
def visualizar(id):
    conn = get_connection()
    cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
    acessos = conn.execute("SELECT * FROM acessos WHERE cliente_id = ?", (id,)).fetchall()
    conn.close()

    if not cliente:
        flash("Cliente não encontrado.", "error")
        return redirect(url_for("clientes.index"))

    dados_acesso = {
        "principal": next((a for a in acessos if a['sistema_servico'] == "Acesso Principal"), None),
        "protheus": next((a for a in acessos if a['sistema_servico'] == "Protheus"), None),
        "banco": next((a for a in acessos if a['sistema_servico'] == "Banco de Dados"), None),
        "anydesk": next((a for a in acessos if a['sistema_servico'] == "AnyDesk"), None),
        "windows": next((a for a in acessos if a['sistema_servico'] == "Windows"), None),
    }

    return render_template("clientes_visualizar.html", cliente=cliente, dados_acesso=dados_acesso)

@clientes_bp.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    if session.get("usuario_nivel") != "ADM" and "clientes_editar" not in session.get("usuario_permissoes", ""):
        flash("Acesso negado para editar clientes.", "error")
        return redirect(url_for("clientes.index"))

    conn = get_connection()
    cliente = conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
    acessos = conn.execute("SELECT * FROM acessos WHERE cliente_id = ?", (id,)).fetchall()

    if not cliente:
        flash("Cliente não encontrado.", "error")
        conn.close()
        return redirect(url_for("clientes.index"))
        
    dados_acesso = {
        "principal": next((a for a in acessos if a['sistema_servico'] == "Acesso Principal"), None),
        "protheus": next((a for a in acessos if a['sistema_servico'] == "Protheus"), None),
        "banco": next((a for a in acessos if a['sistema_servico'] == "Banco de Dados"), None),
        "anydesk": next((a for a in acessos if a['sistema_servico'] == "AnyDesk"), None),
        "windows": next((a for a in acessos if a['sistema_servico'] == "Windows"), None),
    }

    if request.method == "POST":
        nome_empresa = str(request.form.get("nome_empresa", ""))
        nome_identificacao = str(request.form.get("nome_identificacao", ""))
        tipo_cliente = str(request.form.get("tipo_cliente", ""))
        versao_protheus = str(request.form.get("versao_protheus", ""))
        observacoes = str(request.form.get("observacoes", ""))
        status = str(request.form.get("status", "ativo"))
        
        url_acesso = str(request.form.get("url_acesso", ""))
        login_acesso = str(request.form.get("login_acesso", ""))
        senha_acesso = str(request.form.get("senha_acesso", ""))
        
        protheus_login = str(request.form.get("protheus_login", ""))
        protheus_senha = str(request.form.get("protheus_senha", ""))
        
        db_login = str(request.form.get("db_login", ""))
        db_senha = str(request.form.get("db_senha", ""))

        anydesk_login = str(request.form.get("anydesk_login", ""))
        anydesk_senha = str(request.form.get("anydesk_senha", ""))
        
        windows_login = str(request.form.get("windows_login", ""))
        windows_senha = str(request.form.get("windows_senha", ""))
        
        portal_url = str(request.form.get("portal_url", ""))
        portal_login = str(request.form.get("portal_login", ""))
        portal_senha = str(request.form.get("portal_senha", ""))

        imagem_path = str(cliente["imagem_path"]) if cliente["imagem_path"] else ""
        file = request.files.get('imagem')
        
        if file and file.filename:
            filename_str = str(file.filename)
            if filename_str != '' and allowed_file(filename_str):
                if imagem_path:
                    old_path = os.path.join(current_app.root_path, 'static', 'uploads', imagem_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(filename_str)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                imagem_path = unique_filename

        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE clientes SET nome_empresa=?, nome_identificacao=?, imagem_path=?, tipo_cliente=?, versao_protheus=?, observacoes=?,
                                    portal_url=?, portal_login=?, portal_senha=?, status=?, atualizado_em=datetime('now','localtime')
                WHERE id=?
            """, (nome_empresa, nome_identificacao, imagem_path, tipo_cliente, versao_protheus, observacoes,
                  portal_url, portal_login, portal_senha, status, id))
            
            # Função interna corrigida para não dar alerta de tipo
            def salvar_acesso(tipo_acesso: str, login: str, senha: str, url: str = ""):
                existente = next((a for a in acessos if a['sistema_servico'] == tipo_acesso), None)
                ambiente_id = 1
                if tipo_acesso == "Acesso Principal":
                    ambiente_nome = "T-CLOUD" if tipo_cliente == "T-CLOUD" else "LOCAL"
                    amb = conn.execute("SELECT id FROM ambientes WHERE nome = ?", (ambiente_nome,)).fetchone()
                    if amb: ambiente_id = amb["id"]

                if login or senha or url:
                    if existente:
                        cursor.execute("UPDATE acessos SET ambiente_id=?, usuario_login=?, senha_cripto=?, endereco=?, atualizado_em=datetime('now','localtime') WHERE id=?", 
                                       (ambiente_id, login, senha, url, existente['id']))
                    else:
                        cursor.execute("INSERT INTO acessos (cliente_id, ambiente_id, sistema_servico, usuario_login, senha_cripto, endereco) VALUES (?, ?, ?, ?, ?, ?)", 
                                       (id, ambiente_id, tipo_acesso, login, senha, url))
                elif existente:
                    cursor.execute("DELETE FROM acessos WHERE id = ?", (existente['id'],))

            salvar_acesso("Acesso Principal", login_acesso, senha_acesso, url_acesso)
            salvar_acesso("Protheus", protheus_login, protheus_senha)
            salvar_acesso("Banco de Dados", db_login, db_senha)
            salvar_acesso("AnyDesk", anydesk_login, anydesk_senha)
            salvar_acesso("Windows", windows_login, windows_senha)

            conn.commit()
            registrar_log(conn, "EDITAR", "Cliente", id, f"Alterou os dados do cliente {nome_empresa}")
            
            flash("Cliente atualizado com sucesso!", "success")
            return redirect(url_for("clientes.index"))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao atualizar cliente: {str(e)}", "error")
        finally:
            conn.close()

    return render_template("clientes_editar.html", cliente=cliente, dados_acesso=dados_acesso)

@clientes_bp.route("/clientes/excluir/<int:id>")
@login_required
def excluir(id):
    if session.get("usuario_nivel") != "ADM" and "clientes_excluir" not in session.get("usuario_permissoes", ""):
        flash("Acesso negado para excluir clientes.", "error")
        return redirect(url_for("clientes.index"))

    conn = get_connection()
    try:
        cliente = conn.execute("SELECT nome_empresa, imagem_path FROM clientes WHERE id = ?", (id,)).fetchone()
        if cliente and cliente['imagem_path']:
            img_path = os.path.join(current_app.root_path, 'static', 'uploads', str(cliente['imagem_path']))
            if os.path.exists(img_path):
                os.remove(img_path)
                
        conn.execute("DELETE FROM acessos WHERE cliente_id = ?", (id,))
        conn.execute("DELETE FROM clientes WHERE id = ?", (id,))
        conn.commit()
        
        nome_cliente = cliente['nome_empresa'] if cliente else f"ID {id}"
        registrar_log(conn, "EXCLUIR", "Cliente", id, f"Excluiu o cliente {nome_cliente}")
        
        flash("Cliente excluído com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao excluir: {str(e)}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("clientes.index"))