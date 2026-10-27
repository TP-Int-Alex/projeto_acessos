import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_connection

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
    ph = PasswordHasher()
    ARGON2_DISPONIVEL = True
except ImportError:
    ARGON2_DISPONIVEL = False

auth_bp = Blueprint("auth", __name__)

# --- DECORADORES ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Você precisa fazer login.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                flash("Você precisa fazer login.", "error")
                return redirect(url_for("auth.login"))
            if session.get("usuario_nivel") not in roles:
                flash("Acesso negado. Permissão insuficiente.", "error")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permissao_required(permissao):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                flash("Você precisa fazer login.", "error")
                return redirect(url_for("auth.login"))
            if session.get("usuario_nivel") == "ADM":
                return f(*args, **kwargs)
                
            permissoes = session.get("usuario_permissoes", "")
            if permissao not in permissoes:
                flash("Acesso negado. Você não tem permissão para isso.", "error")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- ROTA DE LOGIN ---
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        conn = get_connection()
        usuario = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if usuario:
            senha_valida = False
            hash_salvo = usuario["password_hash"]
            
            try:
                senha_valida = check_password_hash(hash_salvo, password)
            except ValueError:
                pass
                
            if not senha_valida and ARGON2_DISPONIVEL:
                try:
                    senha_valida = ph.verify(hash_salvo, password)
                except (VerifyMismatchError, VerificationError, InvalidHash):
                    senha_valida = False
                
            if senha_valida:
                if "ativo" in usuario.keys() and usuario["ativo"] == 0:
                    flash("Sua conta está desativada.", "error")
                    return render_template("login.html")

                session["usuario_id"] = usuario["id"]
                session["usuario_nome"] = usuario["username"]
                session["usuario_nivel"] = usuario["role"]
                # Pega as permissões (se existirem, senão vazio)
                session["usuario_permissoes"] = usuario["permissoes"] if "permissoes" in usuario.keys() and usuario["permissoes"] else ""
                return redirect(url_for("dashboard.index"))
            else:
                flash("Senha incorreta.", "error")
        else:
            flash("Usuário não encontrado.", "error")
            
    return render_template("login.html")

# --- ROTA DE CADASTRO ---
@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "error")
            return redirect(url_for("auth.cadastro"))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Por favor, insira um e-mail válido.", "error")
            return redirect(url_for("auth.cadastro"))

        conn = get_connection()
        
        if conn.execute("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email)).fetchone():
            conn.close()
            flash("Usuário ou e-mail já cadastrado.", "error")
            return redirect(url_for("auth.cadastro"))

        try:
            senha_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO usuarios (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, senha_hash, "USER")
            )
            conn.commit()
            conn.close()
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Erro ao criar conta: {str(e)}", "error")
            return redirect(url_for("auth.cadastro"))

    return render_template("cadastro.html")

# --- ROTA DE ESQUECI A SENHA ---
@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        flash("Se o e-mail existir, um link de recuperação foi enviado.", "success")
        return redirect(url_for("auth.esqueci_senha"))
    return render_template("esqueci_senha.html")

# --- ROTA DE LOGOUT ---
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))