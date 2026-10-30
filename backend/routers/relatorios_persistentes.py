
import copy
import uuid

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db

from models import (
    Analise,
    Enfermeiro,
    HistoricoEdicao,
    RelatorioIA,
)

from routers.auth import obter_enfermeiro_atual

from schemas.relatorio_persistente import (
    RelatorioSalvar,
    RelatorioEditar,
    RelatorioResposta,
)


router = APIRouter(
    prefix="/analises/{analise_id}/relatorios",
    tags=["Relatorios Persistentes"],
)


# ============================================================
# AUTORIZAÇÃO
# ============================================================

def obter_analise_autorizada(
    analise_id: int,
    enfermeiro: Enfermeiro,
    db: Session,
) -> Analise:

    analise = db.scalar(
        select(Analise).where(
            Analise.id_analise == analise_id,
            Analise.id_enfermeiro_fk == (
                enfermeiro.id_enfermeiro
            ),
            Analise.deleted_at.is_(None),
        )
    )

    if analise is None:
        raise HTTPException(
            status_code=404,
            detail="Analise nao encontrada.",
        )

    return analise


def obter_relatorio_autorizado(
    analise_id: int,
    provedor: str,
    enfermeiro: Enfermeiro,
    db: Session,
) -> RelatorioIA:

    obter_analise_autorizada(
        analise_id,
        enfermeiro,
        db,
    )

    relatorio = db.scalar(
        select(RelatorioIA).where(
            RelatorioIA.id_analise_fk == analise_id,
            RelatorioIA.provedor == provedor,
        )
    )

    if relatorio is None:
        raise HTTPException(
            status_code=404,
            detail="Relatorio nao encontrado.",
        )

    return relatorio


# ============================================================
# SERIALIZAÇÃO
# ============================================================

def serializar_relatorio(
    relatorio: RelatorioIA,
) -> dict:

    return RelatorioResposta(
        id_relatorio=relatorio.id_relatorio,
        id_analise_fk=relatorio.id_analise_fk,
        provedor=relatorio.provedor,
        conteudo_original=relatorio.conteudo_original,
        conteudo_editavel=relatorio.conteudo_editavel,
        status=relatorio.status,
        alertas_validacao=relatorio.alertas_validacao,
        revisao_profissional_necessaria=(
            relatorio.revisao_profissional_necessaria
        ),
        profissional_responsavel_fk=(
            relatorio.profissional_responsavel_fk
        ),
        data_aprovacao=relatorio.data_aprovacao,
    ).model_dump(mode="json")


# ============================================================
# SALVAR RELATÓRIO
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def salvar_relatorio(
    analise_id: int,
    dados: RelatorioSalvar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    obter_analise_autorizada(
        analise_id,
        enfermeiro,
        db,
    )

    existente = db.scalar(
        select(RelatorioIA).where(
            RelatorioIA.id_analise_fk == analise_id,
            RelatorioIA.provedor == dados.provedor,
        )
    )

    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ja existe relatorio deste provedor "
                "para esta analise."
            ),
        )

    relatorio = RelatorioIA(
        id_relatorio=str(uuid.uuid4()),
        id_analise_fk=analise_id,
        provedor=dados.provedor,
        conteudo_original=copy.deepcopy(
            dados.conteudo
        ),
        conteudo_editavel=copy.deepcopy(
            dados.conteudo
        ),
        status="gerado",
        alertas_validacao=dados.alertas_validacao,
        revisao_profissional_necessaria=True,
    )

    db.add(relatorio)

    try:
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Relatorio duplicado ou conflito de dados.",
        ) from erro
    except Exception:
        db.rollback()
        raise

    db.refresh(relatorio)

    return {
        "sucesso": True,
        "mensagem": "Relatorio salvo no MySQL.",
        "relatorio": serializar_relatorio(relatorio),
    }


# ============================================================
# LISTAR RELATÓRIOS
# ============================================================

@router.get("")
def listar_relatorios(
    analise_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    obter_analise_autorizada(
        analise_id,
        enfermeiro,
        db,
    )

    relatorios = db.scalars(
        select(RelatorioIA)
        .where(
            RelatorioIA.id_analise_fk == analise_id
        )
        .order_by(RelatorioIA.provedor)
    ).all()

    return {
        "sucesso": True,
        "id_analise": analise_id,
        "total": len(relatorios),
        "relatorios": [
            serializar_relatorio(relatorio)
            for relatorio in relatorios
        ],
    }


# ============================================================
# CONSULTAR RELATÓRIO
# ============================================================

@router.get("/{provedor}")
def consultar_relatorio(
    analise_id: int,
    provedor: str,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    relatorio = obter_relatorio_autorizado(
        analise_id,
        provedor,
        enfermeiro,
        db,
    )

    return {
        "sucesso": True,
        "relatorio": serializar_relatorio(relatorio),
    }


# ============================================================
# EDITAR RELATÓRIO
# ============================================================

@router.patch("/{provedor}")
def editar_relatorio(
    analise_id: int,
    provedor: str,
    dados: RelatorioEditar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    relatorio = obter_relatorio_autorizado(
        analise_id,
        provedor,
        enfermeiro,
        db,
    )

    if relatorio.status == "aprovado":
        raise HTTPException(
            status_code=409,
            detail=(
                "Relatorio aprovado nao pode "
                "ser editado."
            ),
        )

    conteudo = copy.deepcopy(
        relatorio.conteudo_editavel
    )

    if dados.campo not in conteudo:
        raise HTTPException(
            status_code=400,
            detail=(
                "Campo nao encontrado no relatorio. "
                "Esta rota edita apenas campos "
                "do primeiro nivel."
            ),
        )

    valor_anterior = copy.deepcopy(
        conteudo[dados.campo]
    )

    if valor_anterior == dados.novo_valor:
        return {
            "sucesso": True,
            "mensagem": "Nenhuma alteracao necessaria.",
            "relatorio": serializar_relatorio(relatorio),
        }

    conteudo[dados.campo] = dados.novo_valor

    relatorio.conteudo_editavel = conteudo
    relatorio.status = "em_edicao"

    historico = HistoricoEdicao(
        id_relatorio_fk=relatorio.id_relatorio,
        id_enfermeiro_fk=enfermeiro.id_enfermeiro,
        campo=dados.campo,
        valor_anterior=valor_anterior,
        valor_novo=dados.novo_valor,
    )

    db.add(historico)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(relatorio)

    return {
        "sucesso": True,
        "mensagem": "Relatorio atualizado.",
        "relatorio": serializar_relatorio(relatorio),
    }


# ============================================================
# APROVAR RELATÓRIO
# ============================================================

@router.post("/{provedor}/aprovar")
def aprovar_relatorio_endpoint(
    analise_id: int,
    provedor: str,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    relatorio = obter_relatorio_autorizado(
        analise_id,
        provedor,
        enfermeiro,
        db,
    )

    if relatorio.status == "aprovado":
        raise HTTPException(
            status_code=409,
            detail="Relatorio ja aprovado.",
        )

    relatorio.status = "aprovado"

    relatorio.profissional_responsavel_fk = (
        enfermeiro.id_enfermeiro
    )

    relatorio.data_aprovacao = datetime.now()

    relatorio.revisao_profissional_necessaria = False

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(relatorio)

    return {
        "sucesso": True,
        "mensagem": (
            "Relatorio aprovado pelo enfermeiro."
        ),
        "relatorio": serializar_relatorio(relatorio),
    }


# ============================================================
# CONSULTAR HISTÓRICO DE EDIÇÕES
# ============================================================

@router.get("/{provedor}/historico")
def consultar_historico(
    analise_id: int,
    provedor: str,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    relatorio = obter_relatorio_autorizado(
        analise_id,
        provedor,
        enfermeiro,
        db,
    )

    historico = db.scalars(
        select(HistoricoEdicao)
        .where(
            HistoricoEdicao.id_relatorio_fk == (
                relatorio.id_relatorio
            )
        )
        .order_by(
            HistoricoEdicao.data_edicao.desc(),
            HistoricoEdicao.id_edicao.desc(),
        )
    ).all()

    return {
        "sucesso": True,
        "id_relatorio": relatorio.id_relatorio,
        "provedor": provedor,
        "total_edicoes": len(historico),
        "historico": [
            {
                "id_edicao": item.id_edicao,
                "id_enfermeiro": item.id_enfermeiro_fk,
                "campo": item.campo,
                "valor_anterior": item.valor_anterior,
                "valor_novo": item.valor_novo,
                "data_edicao": item.data_edicao.isoformat(),
            }
            for item in historico
        ],
    }
