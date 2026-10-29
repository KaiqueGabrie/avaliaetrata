
from sqlalchemy import inspect

from database import Base, engine

# Importa todos os modelos
import models


def testar_models():
    print("=" * 55)
    print("AVALIA & TRATA - TESTE DOS MODELOS SQLALCHEMY")
    print("=" * 55)

    try:
        inspetor = inspect(engine)

        tabelas_mysql = set(inspetor.get_table_names())
        tabelas_models = set(Base.metadata.tables.keys())

        print(f"\nTabelas no MySQL: {len(tabelas_mysql)}")
        print(f"Modelos SQLAlchemy: {len(tabelas_models)}")

        print("\nVerificacao das tabelas:")

        for tabela in sorted(tabelas_models):
            if tabela in tabelas_mysql:
                print(f"[OK] {tabela}")
            else:
                print(f"[ERRO] {tabela} nao encontrada")

        faltando = tabelas_models - tabelas_mysql

        if not faltando and len(tabelas_models) == 10:
            print("\nSUCESSO!")
            print("Todos os 10 modelos foram reconhecidos.")
        else:
            print("\nATENCAO!")
            print("Verifique as tabelas e os modelos.")

    except Exception as erro:
        print(f"\nErro durante o teste: {erro}")


if __name__ == "__main__":
    testar_models()
