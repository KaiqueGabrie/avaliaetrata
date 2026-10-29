
import os

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Enfermeiro, LogAuditoria

from schemas.auth import (
    CadastroEnfermeiro,
    LoginEnfermeiro,
    EnfermeiroResposta,
    TokenResposta,
)

from services.seguranca import (
    gerar_hash_senha,
    verificar_senha,
    criar_token_acesso,
    decodificar_token,
    JWT_EXPIRACAO_MINUTOS,
)


router = APIRouter(
    prefix="/auth",
    tags=["Autenticacao"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def registrar_auditoria(
    db: Session,
    acao: str,
    id_enfermeiro: int,
    detalhes: dict | None = None,
):
    log = LogAuditoria(
        id_enfermeiro_fk=id_enfermeiro,
        acao=acao,
        entidade="enfermeiro",
        registro_id=str(id_enfermeiro),
        detalhes=detalhes,
    )
    db.add(log)


def obter_enfermeiro_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> Enfermeiro:

    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if (
        credenciais is None
        or credenciais.scheme.lower() != "bearer"
    ):
        raise erro

    id_enfermeiro = decodificar_token(
        credenciais.credentials
    )

    if id_enfermeiro is None:
        raise erro

    enfermeiro = db.get(
        Enfermeiro,
        id_enfermeiro,
    )

    if (
        enfermeiro is None
        or enfermeiro.deleted_at is not None
    ):
        raise erro

    return enfermeiro


@router.post(
    "/cadastro",
    response_model=EnfermeiroResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_enfermeiro(
    dados: CadastroEnfermeiro,
    db: Session = Depends(get_db),
):
    # Cadastro publico desativado por padrao.
    # Habilitar somente em ambiente local de teste.
    if os.getenv(
        "ALLOW_TEST_REGISTRATION", "false"
    ).lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="Cadastro publico desabilitado.",
        )

    existente = db.scalar(
        select(Enfermeiro).where(
            or_(
                Enfermeiro.email == dados.email,
                Enfermeiro.cpf == dados.cpf,
            )
        )
    )

    if existente:
        raise HTTPException(
            status_code=409,
            detail="Email ou CPF ja cadastrado.",
        )

    enfermeiro = Enfermeiro(
        nome=dados.nome,
        email=dados.email,
        senha=gerar_hash_senha(dados.senha),
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        telefone=dados.telefone,
        registro_coren=dados.registro_coren,
    )

    try:
        db.add(enfermeiro)
        db.flush()

        registrar_auditoria(
            db=db,
            acao="CADASTRO_ENFERMEIRO",
            id_enfermeiro=enfermeiro.id_enfermeiro,
            detalhes={
                "origem": "cadastro_teste",
            },
        )

        db.commit()
        db.refresh(enfermeiro)

        return enfermeiro

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email ou CPF ja cadastrado.",
        )


@router.post(
    "/login",
    response_model=TokenResposta,
)
def login(
    dados: LoginEnfermeiro,
    db: Session = Depends(get_db),
):
    email = dados.email.strip().lower()

    enfermeiro = db.scalar(
        select(Enfermeiro).where(
            Enfermeiro.email == email,
            Enfermeiro.deleted_at.is_(None),
        )
    )

    # Mesmo hash ficticio para reduzir diferencas
    # de processamento quando o usuario nao existe.
    if enfermeiro is None:
        gerar_hash_senha(dados.senha)
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos.",
        )

    if not verificar_senha(
        dados.senha,
        enfermeiro.senha,
    ):
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos.",
        )

    token = criar_token_acesso(
        enfermeiro.id_enfermeiro
    )

    registrar_auditoria(
        db=db,
        acao="LOGIN_SUCESSO",
        id_enfermeiro=enfermeiro.id_enfermeiro,
        detalhes={
            "metodo": "senha",
        },
    )

    db.commit()

    return TokenResposta(
        access_token=token,
        expires_in=JWT_EXPIRACAO_MINUTOS * 60,
    )


@router.get(
    "/me",
    response_model=EnfermeiroResposta,
)
def consultar_perfil(
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):
    return enfermeiro
