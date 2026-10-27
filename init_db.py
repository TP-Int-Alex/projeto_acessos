from database.db import init_db
from services.auth_service import criar_usuario_inicial

if __name__ == "__main__":
    init_db()
    criar_usuario_inicial("ADM", "admin123", "ADM")
    criar_usuario_inicial("ALEX", "123", "USER")
    print("Banco inicializado com usuários ADM e ALEX.")