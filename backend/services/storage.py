"""Armazenamento privado das imagens no Supabase Storage.

Os caminhos persistidos no MySQL possuem o prefixo supabase:.
As chaves secretas ficam exclusivamente no backend.
"""
import logging
import os
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from supabase import Client, create_client

logger = logging.getLogger(__name__)
PREFIXO_STORAGE = "supabase:"


def storage_ativo() -> bool:
    configurado = all(
        os.getenv(nome, "").strip()
        for nome in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_BUCKET")
    )
    obrigatorio = os.getenv("STORAGE_REQUIRED", "false").lower() == "true"
    if obrigatorio and not configurado:
        raise RuntimeError("Supabase Storage obrigatorio, mas nao configurado.")
    return configurado


@lru_cache(maxsize=1)
def obter_cliente() -> Client:
    if not storage_ativo():
        raise RuntimeError("Supabase Storage nao configurado.")
    return create_client(
        os.environ["SUPABASE_URL"].strip(),
        os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip(),
    )


def bucket():
    return obter_cliente().storage.from_(os.environ["SUPABASE_BUCKET"].strip())


def criar_chave(tipo: str, enfermeiro_id: int, paciente_id: int,
                analise_id: int, extensao: str) -> str:
    if tipo not in ("originais", "processadas", "bordas", "marcacoes"):
        raise ValueError("Tipo de imagem invalido.")
    extensao = extensao.lower()
    if extensao not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValueError("Extensao invalida.")
    return (
        f"{tipo}/{enfermeiro_id}/{paciente_id}/{analise_id}/"
        f"{uuid4().hex}{extensao}"
    )


def enviar_arquivo(caminho: Path, chave: str) -> str:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError("Imagem nao encontrada para upload.")
    tipos = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".png": "image/png", ".webp": "image/webp"}
    mime = tipos.get(caminho.suffix.lower())
    if not mime:
        raise ValueError("Tipo de imagem nao permitido.")
    bucket().upload(
        path=chave,
        file=caminho.read_bytes(),
        file_options={"content-type": mime, "upsert": "false"},
    )
    return PREFIXO_STORAGE + chave


def baixar_original(chave: str, destino: Path) -> Path:
    if not chave.startswith("originais/") or ".." in Path(chave).parts:
        raise ValueError("Chave de imagem original invalida.")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(bucket().download(chave))
    return destino


def remover_remotos(chaves: list[str]) -> None:
    if not chaves:
        return
    try:
        bucket().remove(chaves)
    except Exception:
        logger.exception("Nao foi possivel limpar arquivos remotos.")


def url_assinada(chave: str, segundos: int = 300) -> str | None:
    try:
        resposta = bucket().create_signed_url(chave, segundos)
        return (
            resposta.get("signedURL")
            or resposta.get("signedUrl")
            or resposta.get("signed_url")
        )
    except Exception:
        logger.exception("Nao foi possivel gerar URL privada temporaria.")
        return None
