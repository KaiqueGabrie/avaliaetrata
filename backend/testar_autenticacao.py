
from uuid import uuid4

from sqlalchemy import select

from database import SessionLocal
from models import Enfermeiro
from services.seguranca import (
    gerar_hash_senha,
    verificar_senha,
)


def testar_autenticacao():
    print("=" * 55)
    print("AVALIA & TRATA - TESTE DE SENHAS E PERSISTENCIA")
    print("=" * 55)

    senha_teste = "SenhaFicticiaDeTeste#2026"

    # Identificador aleatorio para evitar conflito
    # com outros registros de teste.
    identificador = uuid4().hex[:12]

    email_teste = (
        f"teste_{identificador}@example.invalid"
    )

    cpf_teste = None
    enfermeiro_id = None

    # -------------------------------------------------
    # 1. Testar a protecao da senha
    # -------------------------------------------------
    print("\n1. Testando hash de senha...")

    hash_gerado = gerar_hash_senha(senha_teste)

    assert hash_gerado != senha_teste
    assert verificar_senha(senha_teste, hash_gerado)
    assert not verificar_senha(
        "SenhaIncorreta",
        hash_gerado
    )

    print("[OK] Hash gerado corretamente.")
    print("[OK] Senha correta validada.")
    print("[OK] Senha incorreta rejeitada.")

    # -------------------------------------------------
    # 2. Gravar enfermeiro ficticio
    # -------------------------------------------------
    print("\n2. Gravando enfermeiro no MySQL...")

    try:
        with SessionLocal() as db:
            enfermeiro = Enfermeiro(
                nome="Enfermeiro Ficticio de Teste",
                email=email_teste,
                senha=hash_gerado,
                cpf=f"9{uuid4().int % 10**10:010d}",
                registro_coren="TESTE"
            )

            db.add(enfermeiro)
            db.commit()
            db.refresh(enfermeiro)

            enfermeiro_id = enfermeiro.id_enfermeiro

            print("[OK] Registro salvo com commit().")

        # -------------------------------------------------
        # 3. Consultar em outra sessao
        # -------------------------------------------------
        print("\n3. Consultando em nova sessao...")

        with SessionLocal() as db:
            encontrado = db.scalar(
                select(Enfermeiro).where(
                    Enfermeiro.id_enfermeiro
                    == enfermeiro_id
                )
            )

            assert encontrado is not None
            assert encontrado.email == email_teste

            assert verificar_senha(
                senha_teste,
                encontrado.senha
            )

            print("[OK] Registro encontrado.")
            print("[OK] Senha validada com hash salvo.")
            print("[OK] Persistencia confirmada.")

        print("\nSUCESSO!")
        print("Autenticacao basica e MySQL funcionando.")

    except Exception as erro:
        print(f"\nERRO NO TESTE: {erro}")

    finally:
        # -------------------------------------------------
        # 4. Limpar registro ficticio
        # -------------------------------------------------
        if enfermeiro_id is not None:
            try:
                with SessionLocal() as db:
                    encontrado = db.get(
                        Enfermeiro,
                        enfermeiro_id
                    )

                    if (
                        encontrado is not None
                        and encontrado.email == email_teste
                    ):
                        db.delete(encontrado)
                        db.commit()
                        print(
                            "\nRegistro ficticio removido."
                        )

            except Exception as erro:
                print(
                    "\nATENCAO: nao foi possivel "
                    f"remover o teste: {erro}"
                )


if __name__ == "__main__":
    testar_autenticacao()
