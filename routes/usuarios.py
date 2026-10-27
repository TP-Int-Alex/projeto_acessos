from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from database.db import get_connection
from routes.auth import role_required

usuarios_bp = Blueprint("usuarios", __name__)

def registrar_log(conn, operacao, entidade, entidade_id, detalhes=""):
    try:
        usuario_id = session.get("usuario_id")
        username = session.get("usuario_nome", "Sistema")
        ip = request.remote_addr
        conn.execute("""
            INSERT INTO logs_auditoria (usuario_id, username, operacao, entidade, entidade_id, valor_novo, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (usuario_id, username, operacao, entidade, entidade_id, detalhes, ip))
        conn.commit()
    except Exception as e:
        print(f"Erro ao gravar log: {e}")

@usuarios_bp.route("/usuarios", methods=["GET", "POST"])
@role_required("ADM")
def index():
    conn = get_connection()
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "USER")
        
        permissoes_lista = request.form.getlist("permissoes")
        permissoes_str = ",".join(permissoes_lista)

        if len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "error")
            return redirect(url_for("usuarios.index"))

        if conn.execute("SELECT id FROM usuarios WHERE username = ?", (username,)).fetchone():
            conn.close()
            flash("Usuário já cadastrado.", "error")
            return redirect(url_for("usuarios.index"))

        try:
            senha_hash = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, email, password_hash, role, permissoes, ativo) VALUES (?, ?, ?, ?, ?, 1)",
                (username, email, senha_hash, role, permissoes_str)
            )
            conn.commit()
            
            # GRAVA O LOG
            novo_id = cursor.lastrowid
            registrar_log(conn, "CRIAR", "Usuário", novo_id, f"Criou o usuário {username} com nível {role}")
            
            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for("usuarios.index"))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar: {str(e)}", "error")
        finally:
            conn.close()

    usuarios = conn.execute("SELECT * FROM usuarios ORDER BY username").fetchall()
    conn.close()
    
    return render_template("usuarios.html", usuarios=usuarios)

@usuarios_bp.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@role_required("ADM")
def editar(id):
    conn = get_connection()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()

    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("usuarios.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "USER")
        password = request.form.get("password", "")
        
        permissoes_lista = request.form.getlist("permissoes")
        permissoes_str = ",".join(permissoes_lista)

        try:
            if password:
                if len(password) < 4:
                    flash("A nova senha deve ter pelo menos 4 caracteres.", "error")
                    return redirect(url_for("usuarios.editar", id=id))
                senha_hash = generate_password_hash(password)
                conn.execute(
                    "UPDATE usuarios SET email=?, password_hash=?, role=?, permissoes=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                    (email, senha_hash, role, permissoes_str, id)
                )
            else:
                conn.execute(
                    "UPDATE usuarios SET email=?, role=?, permissoes=?, atualizado_em=datetime('now','localtime') WHERE id=?",
                    (email, role, permissoes_str, id)
                )
            conn.commit()
            
            # GRAVA O LOG
            registrar_log(conn, "EDITAR", "Usuário", id, f"Alterou o usuário {usuario['username']}")
            
            flash("Usuário atualizado com sucesso!", "success")
            return redirect(url_for("usuarios.index"))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao atualizar: {str(e)}", "error")
        finally:
            conn.close()

    return render_template("usuarios_editar.html", usuario=usuario)

@usuarios_bp.route("/usuarios/excluir/<int:id>")
@role_required("ADM")
def excluir(id):
    if id == session.get("usuario_id"):
        flash("Você não pode excluir o seu próprio usuário.", "error")
        return redirect(url_for("usuarios.index"))

    conn = get_connection()
    try:
        usuario = conn.execute("SELECT username FROM usuarios WHERE id = ?", (id,)).fetchone()
        nome_usuario = usuario['username'] if usuario else f"ID {id}"
        
        conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        conn.commit()
        
        # GRAVA O LOG
        registrar_log(conn, "EXCLUIR", "Usuário", id, f"Excluiu o usuário {nome_usuario}")
        
        flash("Usuário excluído com sucesso!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao excluir: {str(e)}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("usuarios.index"))