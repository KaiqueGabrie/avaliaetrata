
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from jwt import InvalidTokenError
from pwdlib import PasswordHash


load_dotenv()

password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
JWT_EXPIRACAO_MINUTOS = 60


def gerar_hash_senha(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(
    senha: str,
    hash_armazenado: str
) -> bool:
    return password_hash.verify(senha, hash_armazenado)


def obter_chave_jwt() -> str:
    chave = os.getenv("JWT_SECRET_KEY", "")

    if len(chave) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY deve ter pelo menos "
            "32 caracteres no arquivo .env."
        )

    return chave


def criar_token_acesso(id_enfermeiro: int) -> str:
    agora = datetime.now(timezone.utc)

    payload = {
        "sub": str(id_enfermeiro),
        "iat": agora,
        "exp": agora + timedelta(
            minutes=JWT_EXPIRACAO_MINUTOS
        ),
        "type": "access",
    }

    return jwt.encode(
        payload,
        obter_chave_jwt(),
        algorithm=JWT_ALGORITHM,
    )


def decodificar_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token,
            obter_chave_jwt(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        if payload.get("type") != "access":
            return None

        identificador = int(payload["sub"])

        if identificador <= 0:
            return None

        return identificador

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ):
        return None
