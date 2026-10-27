import os
from flask import Flask, session, abort, render_template, send_from_directory
from config import Config
from database.db import init_db
from services.auth_service import criar_usuario_inicial
from services.csrf_service import csrf_init, csrf_protect
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.clientes import clientes_bp
from routes.usuarios import usuarios_bp
from routes.auditoria import auditoria_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["UPLOAD_FOLDER"] = str(Config.UPLOAD_FOLDER)

    Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)

    init_db()
    criar_usuario_inicial("ADM", "admin123", "ADM")
    criar_usuario_inicial("ALEX", "123", "USER")

    csrf_init(app)

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=session.get('csrf_token', ''))

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(auditoria_bp)

    ROTAS_ISENTAS_CSRF = {
        "auth.login",
        "static",
        "clientes.index",
        "clientes.editar",  
        "clientes.visualizar", 
        "usuarios.index",
        "usuarios.editar",
    }

    @app.before_request
    def _csrf():
        from flask import request as _r
        if _r.endpoint in ROTAS_ISENTAS_CSRF:
            return
        csrf_protect()

    @app.after_request
    def set_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'"
        )
        return resp

    @app.route("/database/<path:_>")
    def block_db(_):
        abort(404)

    # Rota para o Favicon
    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.svg', mimetype='image/svg+xml')

    @app.errorhandler(400)
    def erro_400(e):
        return render_template("erro.html", codigo=400,
                               mensagem=str(e.description)), 400

    @app.errorhandler(403)
    def erro_403(e):
        return render_template("erro.html", codigo=403,
                               mensagem="Acesso negado."), 403

    @app.errorhandler(404)
    def erro_404(e):
        return render_template("erro.html", codigo=404,
                               mensagem="Página não encontrada."), 404

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    return app

if __name__ == "__main__":
    app = create_app()
    print("\n" + "="*60)
    print(" Gestão Acessos — Sistema de Gerenciamento")
    print("="*60)
    print(" Usuários iniciais (troque as senhas!):")
    print("   ADM  / admin123")
    print("   ALEX / 123")
    print(" Acesse: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)