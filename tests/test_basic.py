import unittest
import os, sys, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["SECRET_KEY"] = "test-secret"

from config import Config
Config.DATABASE_PATH = __import__("pathlib").Path(tempfile.mkdtemp()) / "test.db"
Config.KEY_FILE = Config.DATABASE_PATH.parent / "test.key"

from app import create_app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_login_page(self):
        r = self.client.get("/login")
        self.assertEqual(r.status_code, 200)

    def test_login_valido(self):
        r = self.client.post("/login", data={"username": "ADM", "password": "admin123"},
                             follow_redirects=True)
        self.assertIn(b"Dashboard", r.data)

    def test_login_invalido(self):
        r = self.client.post("/login", data={"username": "ADM", "password": "errada"})
        self.assertIn(b"inv", r.data.lower())

    def test_acesso_sem_login(self):
        r = self.client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)

    def test_criar_cliente(self):
        self.client.post("/login", data={"username": "ADM", "password": "admin123"})
        r = self.client.post("/clientes/novo", data={
            "nome_empresa": "Empresa Teste",
            "nome_identificacao": "TESTE",
            "status": "ativo"
        }, follow_redirects=True)
        self.assertIn(b"Empresa Teste", r.data)

if __name__ == "__main__":
    unittest.main()