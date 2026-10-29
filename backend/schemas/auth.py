
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class CadastroEnfermeiro(BaseModel):
    nome: str = Field(min_length=3, max_length=150)
    email: str = Field(min_length=5, max_length=150)
    senha: str = Field(min_length=12, max_length=128)
    cpf: str
    data_nascimento: date | None = None
    telefone: str | None = None
    registro_coren: str = Field(min_length=3, max_length=30)

    @field_validator("nome", "registro_coren")
    @classmethod
    def limpar_texto(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if (
            valor.count("@") != 1
            or "." not in valor.split("@")[1]
            or " " in valor
        ):
            raise ValueError("Email invalido.")
        return valor

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, valor: str) -> str:
        cpf = "".join(c for c in valor if c.isdigit())

        if len(cpf) != 11 or len(set(cpf)) == 1:
            raise ValueError("CPF invalido.")

        for tamanho in (9, 10):
            soma = sum(
                int(cpf[i]) * (tamanho + 1 - i)
                for i in range(tamanho)
            )
            digito = (soma * 10) % 11
            if digito == 10:
                digito = 0

            if digito != int(cpf[tamanho]):
                raise ValueError("CPF invalido.")

        return cpf


class LoginEnfermeiro(BaseModel):
    email: str
    senha: str


class EnfermeiroResposta(BaseModel):
    id_enfermeiro: int
    nome: str
    email: str
    cpf: str
    registro_coren: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
