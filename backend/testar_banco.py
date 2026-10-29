
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine


def testar_conexao():
    print("=" * 50)
    print("AVALIA & TRATA - TESTE DE CONEXAO MYSQL")
    print("=" * 50)

    try:
        with engine.connect() as conexao:
            resultado = conexao.execute(
                text("SELECT DATABASE(), VERSION()")
            )

            banco, versao = resultado.fetchone()

            print("\nConexao realizada com sucesso!")
            print(f"Banco conectado: {banco}")
            print(f"Versao do MySQL: {versao}")
            print("\nBackend pronto para utilizar o MySQL!")

    except SQLAlchemyError as erro:
        print("\nFalha na conexao com o MySQL.")
        print(f"Detalhes tecnicos: {erro}")


if __name__ == "__main__":
    testar_conexao()
