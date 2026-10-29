
from datetime import date

from sqlalchemy import select, func

from database import SessionLocal
from models import (
    InstituicaoSaude,
    Enfermeiro,
    EnfermeiroInstituicao,
    Paciente,
    Anamnese,
    Analise,
)


def testar_persistencia():
    print("=" * 55)
    print("AVALIA & TRATA - TESTE DE PERSISTENCIA MYSQL")
    print("=" * 55)

    db = SessionLocal()

    try:
        # 1. Instituicao ficticia
        instituicao = InstituicaoSaude(
            nome="Instituicao Ficticia de Testes"
        )
        db.add(instituicao)
        db.flush()

        # 2. Enfermeiro ficticio
        # Valor de teste nao representa senha real.
        # A autenticacao sera implementada separadamente.
        enfermeiro = Enfermeiro(
            nome="Enfermeiro de Teste",
            email="teste.persistencia@example.invalid",
            senha="HASH_FICTICIO_NAO_UTILIZAR_EM_PRODUCAO",
            cpf="00000000000",
            registro_coren="TESTE-000"
        )
        db.add(enfermeiro)
        db.flush()

        # 3. Vinculo institucional
        vinculo = EnfermeiroInstituicao(
            id_enfermeiro_fk=enfermeiro.id_enfermeiro,
            id_instituicao_fk=instituicao.id_instituicao,
            data_inicio=date(2026, 1, 1)
        )
        db.add(vinculo)

        # 4. Paciente ficticio
        paciente = Paciente(
            id_enfermeiro_fk=enfermeiro.id_enfermeiro,
            id_instituicao_fk=instituicao.id_instituicao,
            nome_completo="Paciente Ficticio",
            cpf=None
        )
        db.add(paciente)
        db.flush()

        # 5. Anamnese vinculada ao perfil
        anamnese = Anamnese(
            id_paciente_fk=paciente.id_paciente,
            historia_pregressa="Dados simulados para teste.",
            tabagismo=0,
            mobilidade_reduzida=0
        )
        db.add(anamnese)

        # 6. Duas analises para o mesmo paciente
        analise_1 = Analise(
            id_paciente_fk=paciente.id_paciente,
            id_enfermeiro_fk=enfermeiro.id_enfermeiro,
            queixa_principal="Registro ficticio da consulta 1",
            contexto_clinico_json={
                "origem": "teste",
                "historia_pregressa": "Dados simulados para teste."
            }
        )

        analise_2 = Analise(
            id_paciente_fk=paciente.id_paciente,
            id_enfermeiro_fk=enfermeiro.id_enfermeiro,
            queixa_principal="Registro ficticio da consulta 2",
            contexto_clinico_json={
                "origem": "teste",
                "historia_pregressa": "Dados simulados para teste."
            }
        )

        db.add_all([analise_1, analise_2])
        db.flush()

        # 7. Consultar os registros criados
        total_anamneses = db.scalar(
            select(func.count(Anamnese.id_anamnese))
            .where(Anamnese.id_paciente_fk == paciente.id_paciente)
        )

        total_analises = db.scalar(
            select(func.count(Analise.id_analise))
            .where(Analise.id_paciente_fk == paciente.id_paciente)
        )

        print("\nREGISTROS CRIADOS:")
        print(f"Instituicao: {instituicao.nome}")
        print(f"Enfermeiro: {enfermeiro.nome}")
        print(f"Paciente: {paciente.nome_completo}")
        print(f"Anamneses: {total_anamneses}")
        print(f"Analises: {total_analises}")

        assert total_anamneses == 1
        assert total_analises == 2

        print("\nSUCESSO!")
        print("Os relacionamentos funcionaram corretamente.")
        print("Uma anamnese e duas analises para o paciente.")

    except Exception as erro:
        print(f"\nERRO NO TESTE: {erro}")

    finally:
        # Desfaz as insercoes ficticias.
        # Nenhum dado de teste sera confirmado no banco.
        db.rollback()
        db.close()
        print("\nTransacao desfeita. Teste finalizado.")


if __name__ == "__main__":
    testar_persistencia()
