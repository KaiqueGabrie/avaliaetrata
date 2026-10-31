
import os

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
from models import Enfermeiro, LogAuditoria, InstituicaoSaude, EnfermeiroInstituicao

from schemas.auth import (
    CadastroEnfermeiro,
    LoginEnfermeiro,
    EnfermeiroResposta,
    TokenResposta,
    AtualizacaoPerfilEnfermeiro,
    PerfilEnfermeiroResposta,
)

from services.seguranca import (
    gerar_hash_senha,
    verificar_senha,
    criar_token_acesso,
    decodificar_token,
    JWT_EXPIRACAO_MINUTOS,
)


# ==========================================
# CONFIGURACAO DO ROUTER
# ==========================================

router = APIRouter(
    prefix="/auth",
    tags=["Autenticacao"],
)

bearer_scheme = HTTPBearer(auto_error=False)


# ==========================================
# AUDITORIA
# ==========================================

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


# ==========================================
# ENFERMEIRO AUTENTICADO
# ==========================================

def obter_enfermeiro_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> Enfermeiro:

    erro_autenticacao = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credenciais is None:
        raise erro_autenticacao

    if credenciais.scheme.lower() != "bearer":
        raise erro_autenticacao

    id_enfermeiro = decodificar_token(
        credenciais.credentials
    )

    if id_enfermeiro is None:
        raise erro_autenticacao

    enfermeiro = db.get(
        Enfermeiro,
        id_enfermeiro,
    )

    if enfermeiro is None:
        raise erro_autenticacao

    if enfermeiro.deleted_at is not None:
        raise erro_autenticacao

    return enfermeiro


# ==========================================
# CADASTRO DE ENFERMEIRO
# ==========================================

@router.post(
    "/cadastro",
    response_model=EnfermeiroResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_enfermeiro(
    dados: CadastroEnfermeiro,
    db: Session = Depends(get_db),
):

    # Cadastro liberado apenas para testes locais.
    if os.getenv(
        "ALLOW_TEST_REGISTRATION", "false"
    ).lower() != "true":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro publico desabilitado.",
        )

    # Verificar duplicidade de email ou CPF.
    enfermeiro_existente = db.scalar(
        select(Enfermeiro).where(
            or_(
                Enfermeiro.email == dados.email,
                Enfermeiro.cpf == dados.cpf,
            )
        )
    )

    if enfermeiro_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou CPF ja cadastrado.",
        )

    # Gerar hash da senha.
    senha_protegida = gerar_hash_senha(
        dados.senha
    )

    # Criar enfermeiro.
    novo_enfermeiro = Enfermeiro(
        nome=dados.nome,
        email=dados.email,
        senha=senha_protegida,
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        telefone=dados.telefone,
        registro_coren=dados.registro_coren,
    )

    try:
        db.add(novo_enfermeiro)
        db.flush()

        # Registrar cadastro no log.
        registrar_auditoria(
            db=db,
            acao="CADASTRO_ENFERMEIRO",
            id_enfermeiro=novo_enfermeiro.id_enfermeiro,
            detalhes={
                "origem": "cadastro_teste",
            },
        )

        db.commit()
        db.refresh(novo_enfermeiro)

        return novo_enfermeiro

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou CPF ja cadastrado.",
        )


# ==========================================
# LOGIN
# ==========================================

@router.post(
    "/login",
    response_model=TokenResposta,
)
def realizar_login(
    dados: LoginEnfermeiro,
    db: Session = Depends(get_db),
):

    email = dados.email.strip().lower()

    # Buscar enfermeiro ativo.
    enfermeiro = db.scalar(
        select(Enfermeiro).where(
            Enfermeiro.email == email,
            Enfermeiro.deleted_at.is_(None),
        )
    )

    if enfermeiro is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    # Validar senha.
    senha_correta = verificar_senha(
        dados.senha,
        enfermeiro.senha,
    )

    if not senha_correta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    # Gerar token JWT.
    token = criar_token_acesso(
        enfermeiro.id_enfermeiro
    )

    # Registrar login no banco.
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
        token_type="bearer",
        expires_in=JWT_EXPIRACAO_MINUTOS * 60,
    )


# ==========================================
# PERFIL DO ENFERMEIRO AUTENTICADO
# ==========================================

def buscar_instituicao_atual(db: Session, id_enfermeiro: int):
    return db.execute(
        select(EnfermeiroInstituicao, InstituicaoSaude)
        .join(
            InstituicaoSaude,
            EnfermeiroInstituicao.id_instituicao_fk == InstituicaoSaude.id_instituicao,
        )
        .where(
            EnfermeiroInstituicao.id_enfermeiro_fk == id_enfermeiro,
            EnfermeiroInstituicao.data_fim.is_(None),
            InstituicaoSaude.deleted_at.is_(None),
        )
        .order_by(EnfermeiroInstituicao.id_vinculo.desc())
    ).first()


def resposta_perfil(db: Session, enfermeiro: Enfermeiro) -> PerfilEnfermeiroResposta:
    vinculo = buscar_instituicao_atual(db, enfermeiro.id_enfermeiro)
    return PerfilEnfermeiroResposta(
        id_enfermeiro=enfermeiro.id_enfermeiro,
        nome=enfermeiro.nome,
        email=enfermeiro.email,
        cpf=enfermeiro.cpf,
        data_nascimento=enfermeiro.data_nascimento,
        telefone=enfermeiro.telefone,
        registro_coren=enfermeiro.registro_coren,
        instituicao_saude=vinculo[1].nome if vinculo else None,
        created_at=enfermeiro.created_at,
    )


@router.get("/me", response_model=PerfilEnfermeiroResposta)
def consultar_perfil(
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    return resposta_perfil(db, enfermeiro)


@router.patch("/me", response_model=PerfilEnfermeiroResposta)
def atualizar_perfil(
    dados: AtualizacaoPerfilEnfermeiro,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    duplicado = db.scalar(
        select(Enfermeiro).where(
            Enfermeiro.id_enfermeiro != enfermeiro.id_enfermeiro,
            Enfermeiro.deleted_at.is_(None),
            or_(Enfermeiro.email == dados.email, Enfermeiro.cpf == dados.cpf),
        )
    )
    if duplicado is not None:
        raise HTTPException(status_code=409, detail="Email ou CPF ja cadastrado.")

    alterados = []
    for campo in ("nome", "email", "cpf", "data_nascimento", "telefone", "registro_coren"):
        novo_valor = getattr(dados, campo)
        if getattr(enfermeiro, campo) != novo_valor:
            setattr(enfermeiro, campo, novo_valor)
            alterados.append(campo)

    atual = buscar_instituicao_atual(db, enfermeiro.id_enfermeiro)
    nome_atual = atual[1].nome if atual else None
    nome_novo = dados.instituicao_saude
    if (nome_atual or "").casefold() != (nome_novo or "").casefold():
        from datetime import date
        # Encerrar vinculos anteriores, sem apagar o historico.
        vinculos_ativos = db.scalars(
            select(EnfermeiroInstituicao).where(
                EnfermeiroInstituicao.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
                EnfermeiroInstituicao.data_fim.is_(None),
            )
        ).all()
        for vinculo in vinculos_ativos:
            vinculo.data_fim = date.today()
        if nome_novo:
            instituicao = db.scalar(
                select(InstituicaoSaude).where(
                    InstituicaoSaude.nome == nome_novo,
                    InstituicaoSaude.deleted_at.is_(None),
                )
            )
            if instituicao is None:
                instituicao = InstituicaoSaude(nome=nome_novo)
                db.add(instituicao)
                db.flush()
            db.add(EnfermeiroInstituicao(
                id_enfermeiro_fk=enfermeiro.id_enfermeiro,
                id_instituicao_fk=instituicao.id_instituicao,
                data_inicio=date.today(),
            ))
        alterados.append("instituicao_saude")

    if alterados:
        registrar_auditoria(
            db=db,
            acao="ATUALIZACAO_PERFIL",
            id_enfermeiro=enfermeiro.id_enfermeiro,
            detalhes={"campos_alterados": alterados},
        )
    try:
        db.commit()
        db.refresh(enfermeiro)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dados ja cadastrados ou vinculo invalido.")
    return resposta_perfil(db, enfermeiro)
