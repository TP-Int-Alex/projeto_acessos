"""
Proteção CSRF sem dependências externas (baseada em token de sessão).
"""
import secrets
import hmac
from flask import session, request, abort, jsonify

def _get_token():
    tok = session.get("_csrf_token")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf_token"] = tok
    return tok


def csrf_token():
    """Disponibiliza `csrf_token()` nos templates (cria se ainda não existir)."""
    return _get_token()


def csrf_init(app):
    app.jinja_env.globals["csrf_token"] = csrf_token


def csrf_protect():
    """
    Valida o token em métodos mutáveis (POST/PUT/PATCH/DELETE).
    Aceita token via form field `_csrf_token` ou header `X-CSRF-Token`.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
        esperado = session.get("_csrf_token")
        if not sent or not esperado or not hmac.compare_digest(sent, esperado):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"erro": "CSRF inválido"}), 400
            abort(400, description="Token CSRF ausente ou inválido.")