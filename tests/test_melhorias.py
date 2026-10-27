import unittest, os, sys, tempfile, pathlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SECRET_KEY"] = "test-secret"

from config import Config
_tmp = pathlib.Path(tempfile.mkdtemp())
Config.DATABASE_PATH = _tmp / "test.db"
Config.KEY_FILE = _tmp / "test.key"
Config.UPLOAD_FOLDER = _tmp / "uploads"
Config.BACKUP_FOLDER = _tmp / "backups"
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
Config.BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)

from app import create_app
from services.csrf_service import _get_token


class Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _csrf(self):
        """Obtém token CSRF fazendo GET em /login e lendo a sessão."""
        with self.client.session_transaction() as s:
            return s.get("_csrf_token") or _get_token()

    def login(self, u="ADM", p="admin123"):
        with self.client.session_transaction() as s:
            s["_csrf_token"] = "tk"
        return self.client.post("/login",
                                data={"username": u, "password": p, "_csrf_token": "tk"},
                                follow_redirects=True)


class TestMelhorias(Base):
    def test_dashboard(self):
        self.login()
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Dashboard", r.data)

    def test_csrf_bloqueia(self):
        # Sem login, POST sem CSRF → 400
        r = self.client.post("/clientes/novo", data={"nome_empresa": "X"})
        self.assertIn(r.status_code, (302, 400))

    def test_cofre_existe(self):
        self.login()
        r = self.client.get("/clientes/cofre")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Cofre", r.data)

    def test_detalhe_cliente(self):
        self.login()
        with self.client.session_transaction() as s:
            s["_csrf_token"] = "tk"
        self.client.post("/clientes/novo",
                         data={"nome_empresa": "Acme", "status": "ativo", "_csrf_token": "tk"})
        r = self.client.get("/clientes/1")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Acme", r.data)

    def test_arquivar(self):
        self.login()
        with self.client.session_transaction() as s:
            s["_csrf_token"] = "tk"
        self.client.post("/clientes/novo",
                         data={"nome_empresa": "Beta", "status": "ativo", "_csrf_token": "tk"})
        self.client.post("/clientes/1/arquivar", data={"_csrf_token": "tk"})
        r = self.client.get("/clientes/1")
        self.assertIn(b"inativo", r.data)

    def test_backup(self):
        from services.backup_service import criar_backup, verificar_backup
        self.login()
        info = criar_backup()
        v = verificar_backup(info["arquivo"])
        self.assertTrue(v["ok"])

    def test_alex_nao_revela_senha(self):
        # Cria acesso como ADM
        self.login()
        with self.client.session_transaction() as s:
            s["_csrf_token"] = "tk"
        self.client.post("/clientes/novo", data={
            "nome_empresa": "Gama", "sistema_servico": "Protheus",
            "usuario_login": "u", "senha": "s", "ambiente": "T-CLOUD",
            "_csrf_token": "tk"
        })
        # Logout
        self.client.get("/logout")
        # Login como ALEX
        with self.client.session_transaction() as s:
            s["_csrf_token"] = "tk"
        self.client.post("/login", data={"username": "ALEX", "password": "123", "_csrf_token": "tk"})
        r = self.client.get("/clientes/acesso/1/senha")
        self.assertEqual(r.status_code, 302)  # redirecionado por falta de permissão


if __name__ == "__main__":
    unittest.main()