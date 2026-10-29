"""Avalia & Trata — Validador de consistência multimodal v2.2.

Validação estrutural e alertas heurísticos. Não estabelece diagnósticos.
Preserva as interfaces públicas da versão 2.1.
"""
import math
import re
import unicodedata
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from schemas.multimodal import RespostaEstruturadaModelo, ResultadoAnaliseMultimodal

VERSAO_VALIDADOR = "2.2.1"
COMPONENTES = {"T": "Tecido", "I": "Inflamação/infecção", "M": "Umidade", "E": "Bordas", "S": "Pele ao redor"}
STATUS_VALIDOS = {"avaliavel", "parcialmente_avaliavel", "nao_avaliavel"}
CARACTERISTICA_COMPONENTE = {"leito": "T", "bordas": "E", "pele ao redor": "S"}
MAX_EVIDENCIAS_POR_ALERTA = 3

class AlertaValidacao(BaseModel):
    codigo: str
    severidade: str
    componente: Optional[str] = None
    mensagem: str
    evidencias: List[str] = Field(default_factory=list)

class RelatorioValidacao(BaseModel):
    valido_estruturalmente: bool = True
    requer_revisao: bool = False
    total_alertas: int = 0
    alertas: List[AlertaValidacao] = Field(default_factory=list)


def _normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def _contem(texto: str, padroes: List[str]) -> bool:
    return any(re.search(p, texto, re.IGNORECASE) for p in padroes)


def _frases(texto: Any) -> List[str]:
    if not isinstance(texto, str):
        return []
    return [p.strip() for p in re.split(r"[.!?;\n]+", texto) if p.strip()]


def _texto_valido(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _lista_textos(valores: Any) -> List[str]:
    return [v.strip() for v in valores if _texto_valido(v)] if isinstance(valores, (list, tuple)) else []


def _adicionar_alerta(relatorio: RelatorioValidacao, codigo: str, severidade: str,
                      mensagem: str, componente: Optional[str] = None,
                      evidencias: Optional[List[str]] = None) -> None:
    evidencias_limpas = list(dict.fromkeys(_lista_textos(evidencias or [])))
    for alerta in relatorio.alertas:
        if (alerta.codigo, alerta.componente, alerta.mensagem) == (codigo, componente, mensagem):
            for evidencia in evidencias_limpas:
                if evidencia not in alerta.evidencias and len(alerta.evidencias) < MAX_EVIDENCIAS_POR_ALERTA:
                    alerta.evidencias.append(evidencia)
            return
    relatorio.alertas.append(AlertaValidacao(
        codigo=codigo, severidade=severidade, componente=componente,
        mensagem=mensagem, evidencias=evidencias_limpas[:MAX_EVIDENCIAS_POR_ALERTA]))
    if severidade in ("erro", "aviso"):
        relatorio.requer_revisao = True
    if severidade == "erro":
        relatorio.valido_estruturalmente = False


def _mapear_times(resposta):
    return {item.componente: item for item in resposta.avaliacao_times}


def _mapear_caracteristicas(resposta):
    return {_normalizar_texto(item.caracteristica): item for item in resposta.caracteristicas_visuais}


def _verificar_componentes(resposta, relatorio):
    encontrados = {}
    for item in resposta.avaliacao_times:
        letra = item.componente
        if letra not in COMPONENTES:
            _adicionar_alerta(relatorio, "TIMES_DESCONHECIDO", "erro", f"Componente T.I.M.E.S. desconhecido: {letra}.", letra)
            continue
        if letra in encontrados:
            _adicionar_alerta(relatorio, "TIMES_DUPLICADO", "erro", f"O componente {letra} aparece mais de uma vez.", letra)
        encontrados[letra] = item
    for letra in COMPONENTES:
        if letra not in encontrados:
            _adicionar_alerta(relatorio, "TIMES_AUSENTE", "erro", f"O componente {letra} está ausente.", letra)
    for letra, item in encontrados.items():
        observacoes = _lista_textos(item.observacoes_visuais)
        if item.status not in STATUS_VALIDOS:
            _adicionar_alerta(relatorio, "STATUS_TIMES_INVALIDO", "erro", f"O componente {letra} possui status inválido.", letra, [str(item.status)])
        elif item.status == "nao_avaliavel" and observacoes:
            # v2.2: distinguir limitação de achado visual efetivo.
            achados = [o for o in observacoes if not _somente_limitacao(o)]
            if achados:
                _adicionar_alerta(relatorio, "STATUS_CONTRADITORIO", "aviso",
                                  f"O componente {letra} está não avaliável, mas contém possíveis achados visuais.", letra, achados)
        elif item.status in ("avaliavel", "parcialmente_avaliavel") and not observacoes:
            _adicionar_alerta(relatorio, "STATUS_SEM_OBSERVACAO", "aviso",
                              f"O componente {letra} está avaliável ou parcialmente avaliável, mas não possui observações visuais.", letra)


LIMITACAO = [
    r"\bnao (?:e |foi )?possivel\b", r"\bnao (?:pode|permite|visivel|avaliavel|identificavel)\b",
    r"\bsem (?:visibilidade|dados|informacoes|condicoes)\b", r"\b(?:impossivel|indeterminado|inconclusivo)\b",
    r"\b(?:nao se observa|nao foi possivel observar)\b",
]

def _somente_limitacao(texto: str) -> bool:
    frases = _frases(texto)
    return bool(frases) and all(_contem(_normalizar_texto(f), LIMITACAO) for f in frases)


def _verificar_caracteristicas(resposta, relatorio):
    componentes = _mapear_times(resposta)
    encontrados = set()
    for item in resposta.caracteristicas_visuais:
        nome = _normalizar_texto(item.caracteristica)
        if nome in encontrados:
            _adicionar_alerta(relatorio, "CARACTERISTICA_DUPLICADA", "aviso",
                              f"A característica '{nome}' aparece mais de uma vez.", evidencias=[item.descricao])
        encontrados.add(nome)
        if item.status not in STATUS_VALIDOS:
            _adicionar_alerta(relatorio, "STATUS_CARACTERISTICA_INVALIDO", "erro",
                              f"A característica '{nome}' possui status inválido.")
        if item.status == "avaliavel" and not _texto_valido(item.descricao):
            _adicionar_alerta(relatorio, "CARACTERISTICA_SEM_DESCRICAO", "aviso",
                              f"A característica '{nome}' está avaliável, mas não possui descrição.")
        letra = CARACTERISTICA_COMPONENTE.get(nome)
        componente = componentes.get(letra) if letra else None
        if componente is None:
            continue
        if item.status != "nao_avaliavel" and _texto_valido(item.descricao) and not _lista_textos(componente.observacoes_visuais):
            _adicionar_alerta(relatorio, "CARACTERISTICA_SEM_TIMES", "aviso",
                              f"A característica '{nome}' possui descrição visual, mas o componente {letra} não possui observações.", letra, [item.descricao])
        if letra == "T" and nome == "leito":
            continue  # Regra específica evita duplicação de alerta.
        if item.status == "nao_avaliavel" and componente.status == "avaliavel":
            _adicionar_alerta(relatorio, "DIVERGENCIA_STATUS_CARACTERISTICA_TIMES", "aviso",
                              f"A característica '{nome}' está não avaliável, mas o componente {letra} está avaliável.", letra, [item.descricao])


def _textos_de_achados(resposta):
    yield "descricao_geral", None, resposta.conteudo_descricao
    for item in resposta.caracteristicas_visuais:
        nome = _normalizar_texto(item.caracteristica)
        yield f"caracteristica_{nome}", CARACTERISTICA_COMPONENTE.get(nome), item.descricao
    for item in resposta.avaliacao_times:
        for observacao in item.observacoes_visuais:
            yield f"times_{item.componente}", item.componente, observacao


REGRAS_NAO_VISUAIS = {
    "CONSISTENCIA_FISICA": ([r"\bfirmes?\b", r"\bdur[ao]s?\b", r"\bendurecid[ao]s?\b",
                             r"\benrijecid[ao]s?\b", r"\baderid[ao]s?\b", r"\bflutuantes?\b"],
                            "A resposta pode afirmar consistência ou outra propriedade física não confirmável somente por fotografia."),
    "TEMPERATURA": ([r"\btemperatura\s+(?:local\s+)?(?:elevada|aumentada|normal)\b",
                     r"\bcalor\s+local\s+(?:elevado|aumentado|presente)\b", r"\b(?:pele|regiao)\s+quente\b"],
                    "Temperatura e calor local exigem avaliação presencial ou medição apropriada."),
    "DOR": ([r"\bdor\s+(?:presente|ausente|intensa|moderada)\b",
             r"\b(?:paciente|regiao|lesao)\s+(?:apresenta|possui|tem|refere)\s+dor\b"],
            "A presença ou intensidade da dor não pode ser estabelecida somente pela fotografia."),
    "PROFUNDIDADE": ([r"\bprofundidade\s+(?:de|igual\s+a)\s*\d", r"\b(?:lesao|ferida)\s+(?:profunda|superficial)\b"],
                     "A profundidade real não deve ser considerada confirmada somente pela fotografia."),
}

# Modificadores locais de incerteza; não desativam alertas para a frase inteira.
MODIFICADORES = [r"\baparentemente\b", r"\baparencia\s+(?:de|de ser)?\b", r"\bparece\b",
                 r"\bpossivelmente\b", r"\bsugere\b", r"\bvisual(?:mente)?\b",
                 r"\bnao\s+(?:e\s+)?possivel\b", r"\bnao\s+(?:se\s+)?pode\b",
                 r"\b(?:avaliar|verificar|confirmar|investigar|palpar|palpacao)\b",
                 r"\b(?:necessita|requer|depende)\b"]


def _afirmacao_nao_visual(frase: str, padroes: List[str]) -> bool:
    texto = _normalizar_texto(frase)
    # Analisar orações separadas para não confundir afirmação com outra ressalva.
    for oracao in re.split(r"[,;:]|\bmas\b|\bporem\b|\bentretanto\b", texto):
        for padrao in padroes:
            for achado in re.finditer(padrao, oracao):
                prefixo = oracao[max(0, achado.start() - 60):achado.start()]
                # O alerta não deve ser omitido quando a incerteza vem depois do achado.
                if _contem(prefixo, MODIFICADORES):
                    continue
                if re.search(r"\b(?:nao|sem)\s*$", prefixo):
                    continue
                return True
    return False


def _verificar_propriedades_nao_visuais(resposta, relatorio):
    for origem, componente, texto in _textos_de_achados(resposta):
        for frase in _frases(texto):
            for codigo, (padroes, mensagem) in REGRAS_NAO_VISUAIS.items():
                if _afirmacao_nao_visual(frase, padroes):
                    _adicionar_alerta(relatorio, "PROPRIEDADE_NAO_VISUAL_" + codigo,
                                      "aviso", mensagem, componente, [f"{origem}: {frase}"])


VERMELHIDAO = [r"\bavermelhad\w*\b", r"\bvermelhidao\b", r"\beritema\b", r"\bhiperemia\b", r"\brubor\b"]
AUSENCIA_ALTERACOES = [r"\bsem\s+alteracoes\b", r"\bsem\s+sinais\s+de\s+alteracao\b", r"\bcoloracao\s+normal\b"]
AUSENCIA_VERMELHIDAO = [r"\bsem\s+(?:eritema|vermelhidao|hiperemia|rubor)\b",
                       r"\bausencia\s+de\s+(?:eritema|vermelhidao|hiperemia|rubor)\b",
                       r"\bnao\s+(?:ha|apresenta|possui)\s+(?:eritema|vermelhidao|hiperemia|rubor)\b"]
REFERENCIA_PELE = [r"\bpele\s+(?:ao\s+redor|adjacente|circundante|perilesional)\b",
                   r"\b(?:regiao|area)\s+perilesional\b",
                   r"\b(?:coloracao|vermelhidao|eritema|hiperemia|rubor|avermelhad\w*)\b[^.;]{0,35}\b(?:ao\s+redor|adjacente|circundante)\b"]


def _afirma_vermelhidao(texto: str) -> bool:
    return any(_contem(f, VERMELHIDAO) and not _contem(f, AUSENCIA_VERMELHIDAO)
               for f in (_normalizar_texto(p) for p in _frases(texto)))


def _verificar_contradicoes_pele(resposta, relatorio):
    pele = _mapear_caracteristicas(resposta).get("pele ao redor")
    if pele is None or not _texto_valido(pele.descricao):
        return
    texto_pele = _normalizar_texto(pele.descricao)
    frases_pele = [f for f in _frases(resposta.conteudo_descricao)
                   if _contem(_normalizar_texto(f), REFERENCIA_PELE)]
    if (pele.status != "nao_avaliavel" and
            any(_afirma_vermelhidao(f) for f in frases_pele) and
            _contem(texto_pele, AUSENCIA_ALTERACOES + AUSENCIA_VERMELHIDAO)):
        _adicionar_alerta(relatorio, "POSSIVEL_CONTRADICAO_PELE", "aviso",
                          "Há possível divergência entre vermelhidão descrita e ausência de alterações na pele ao redor.",
                          "S", frases_pele + [pele.descricao])
    s = _mapear_times(resposta).get("S")
    if s is not None and _afirma_vermelhidao(pele.descricao):
        texto_s = " ".join(_lista_textos(s.observacoes_visuais))
        if _contem(_normalizar_texto(texto_s), AUSENCIA_ALTERACOES + AUSENCIA_VERMELHIDAO):
            _adicionar_alerta(relatorio, "DIVERGENCIA_PELE_TIMES_S", "aviso",
                              "A descrição da pele ao redor menciona vermelhidão, mas o componente S indica ausência de alterações.",
                              "S", [pele.descricao] + _lista_textos(s.observacoes_visuais))


def _verificar_leito_encoberto(resposta, relatorio):
    leito = _mapear_caracteristicas(resposta).get("leito")
    t = _mapear_times(resposta).get("T")
    if leito is not None and t is not None and leito.status == "nao_avaliavel" and t.status == "avaliavel":
        _adicionar_alerta(relatorio, "LEITO_NAO_VISIVEL_T_AVALIAVEL", "aviso",
                          "O leito está não avaliável, mas T está avaliável. Confirmar que T se limita à superfície visível.",
                          "T", [leito.descricao] + _lista_textos(t.observacoes_visuais))


def _verificar_dados_clinicos(resposta, relatorio):
    dados = resposta.dados_clinicos_organizados
    ausentes = {_normalizar_texto(v) for v in (dados.dados_nao_informados or [])}
    for campo, nome_origem in {"tipo_exsudato": "tipoExsudato", "odor": "odor", "nivel_dor": "nivelDor"}.items():
        valor = getattr(dados, campo, None)
        if valor is not None and str(valor).strip() and (
            _normalizar_texto(campo) in ausentes or _normalizar_texto(nome_origem) in ausentes
        ):
            _adicionar_alerta(relatorio, "DADO_CLINICO_INCONSISTENTE", "aviso",
                              f"O campo clínico '{campo}' possui valor, mas consta como não informado.",
                              evidencias=[str(valor)])


def _verificar_medidas(resposta, relatorio):
    medidas = resposta.medidas
    area = medidas.area_calculada_cm2
    metodo = medidas.metodo_medicao
    if area is None:
        return
    if not _texto_valido(metodo):
        _adicionar_alerta(relatorio, "AREA_SEM_METODO", "erro",
                          "Existe área calculada sem identificação do método de medição.")
    try:
        numero = float(area)
        if not math.isfinite(numero) or numero <= 0:
            _adicionar_alerta(relatorio, "AREA_INVALIDA", "erro",
                              "A área calculada deve ser um número finito maior que zero.", evidencias=[str(area)])
    except (TypeError, ValueError):
        _adicionar_alerta(relatorio, "AREA_NAO_NUMERICA", "erro", "A área calculada não é numérica.", evidencias=[str(area)])
    # v2.2: método textual não comprova calibração. Sinalizar métodos sem referência verificável.
    if _texto_valido(metodo):
        m = _normalizar_texto(metodo)
        if _contem(m, [r"\b(?:estimativa visual|estimado visualmente|apenas imagem|sem escala|sem referencia|sem calibracao)\b"]):
            _adicionar_alerta(relatorio, "AREA_METODO_SEM_CALIBRACAO", "aviso",
                              "O método informado não demonstra escala ou calibração suficiente para uma área física confiável.",
                              evidencias=[metodo])


def _verificar_marcacoes(resposta, relatorio):
    marcacoes = resposta.marcacoes_imagem
    for indice, regiao in enumerate(marcacoes.regioes or []):
        identificador = regiao.identificador or f"regiao_{indice + 1}"
        pontos = regiao.pontos or []
        if len(pontos) < 3:
            _adicionar_alerta(relatorio, "POLIGONO_INCOMPLETO", "erro",
                              f"A região '{identificador}' possui menos de três pontos.")
            continue
        coordenadas = []
        for ponto in pontos:
            try:
                x = float(ponto["x"] if isinstance(ponto, dict) else ponto.x)
                y = float(ponto["y"] if isinstance(ponto, dict) else ponto.y)
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("Coordenada não finita")
                coordenadas.append((x, y))
            except (TypeError, ValueError, KeyError, AttributeError):
                _adicionar_alerta(relatorio, "COORDENADA_INVALIDA", "erro",
                                  f"A região '{identificador}' possui coordenadas inválidas.")
                coordenadas = []
                break
        if not coordenadas:
            continue
        if marcacoes.sistema_coordenadas == "normalizado_0_1" and any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in coordenadas):
            _adicionar_alerta(relatorio, "COORDENADA_FORA_INTERVALO", "erro",
                              f"A região '{identificador}' possui coordenadas fora do intervalo [0, 1].")
        # v2.2: pontos repetidos não formam necessariamente uma região útil.
        if len(set(coordenadas)) < 3:
            _adicionar_alerta(relatorio, "POLIGONO_DEGENERADO", "aviso",
                              f"A região '{identificador}' possui menos de três pontos distintos.")


def validar_resposta(resposta: RespostaEstruturadaModelo) -> RelatorioValidacao:
    """Valida sem modificar a resposta original."""
    relatorio = RelatorioValidacao()
    _verificar_componentes(resposta, relatorio)
    _verificar_caracteristicas(resposta, relatorio)
    _verificar_propriedades_nao_visuais(resposta, relatorio)
    _verificar_contradicoes_pele(resposta, relatorio)
    _verificar_leito_encoberto(resposta, relatorio)
    _verificar_dados_clinicos(resposta, relatorio)
    _verificar_medidas(resposta, relatorio)
    _verificar_marcacoes(resposta, relatorio)
    relatorio.total_alertas = len(relatorio.alertas)
    return relatorio


def validar_resultados(resultado: ResultadoAnaliseMultimodal) -> Dict[str, RelatorioValidacao]:
    return {nome: validar_resposta(provedor.resposta) for nome, provedor in resultado.resultados.items()
            if provedor.sucesso and provedor.resposta is not None}


def adicionar_alertas_revisao(resposta: RespostaEstruturadaModelo,
                              relatorio: RelatorioValidacao) -> RespostaEstruturadaModelo:
    copia = resposta.model_copy(deep=True)
    existentes = set(copia.pontos_para_revisao_profissional)
    for alerta in relatorio.alertas:
        if alerta.severidade not in ("erro", "aviso"):
            continue
        texto = f"[Validação - {alerta.codigo}] {alerta.mensagem}"
        if texto not in existentes:
            copia.pontos_para_revisao_profissional.append(texto)
            existentes.add(texto)
    return copia
