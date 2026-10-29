"""Avalia & Trata — Comparador Multimodal v1.2.

Comparação lexical conservadora de observações visuais T.I.M.E.S.
Não infere diagnóstico nem elege provedor clinicamente correto.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from schemas.multimodal import ResultadoAnaliseMultimodal
from services.multimodal.validador import RelatorioValidacao, validar_resposta

COMPONENTES_TIMES = {"T": "Tecido", "I": "Inflamação/infecção", "M": "Umidade", "E": "Bordas", "S": "Pele ao redor"}
ORDEM_PROVEDORES = ("openai", "gemini", "kimi")

class ObservacaoProvedor(BaseModel):
    provedor: str
    status: str
    observacoes_visuais: List[str] = Field(default_factory=list)
    dados_clinicos_relacionados: List[str] = Field(default_factory=list)
    informacoes_pendentes: List[str] = Field(default_factory=list)
    limitacoes: List[str] = Field(default_factory=list)
    quantidade_alertas: int = 0
    alertas: List[str] = Field(default_factory=list)

class EvidenciaDescritiva(BaseModel):
    provedor: str
    valor_identificado: str
    trecho_original: str

class DivergenciaDescritiva(BaseModel):
    codigo: str
    componente: str
    caracteristica: str
    descricao: str
    evidencias: List[EvidenciaDescritiva] = Field(default_factory=list)
    requer_revisao_profissional: bool = True

class ComparacaoComponente(BaseModel):
    componente: str
    nome: str
    observacoes_por_provedor: Dict[str, ObservacaoProvedor] = Field(default_factory=dict)
    concordancia_status: bool = False
    status_identificados: List[str] = Field(default_factory=list)
    divergencia_status: bool = False
    pontos_para_revisao: List[str] = Field(default_factory=list)
    situacao_descritiva: str = "inconclusiva"
    divergencia_descritiva: bool = False
    divergencias_descritivas: List[DivergenciaDescritiva] = Field(default_factory=list)
    caracteristicas_comparadas: List[str] = Field(default_factory=list)
    observacao_descritiva: str = ""

class ResumoProvedor(BaseModel):
    provedor: str
    sucesso: bool
    tempo_execucao_segundos: Optional[float] = None
    status_resposta: Optional[str] = None
    valido_estruturalmente: Optional[bool] = None
    quantidade_alertas: int = 0
    mensagem_erro: Optional[str] = None

class ResultadoComparacao(BaseModel):
    versao: str = "1.2"
    provedores_comparados: List[str] = Field(default_factory=list)
    provedores_indisponiveis: List[str] = Field(default_factory=list)
    resumos_provedores: Dict[str, ResumoProvedor] = Field(default_factory=dict)
    componentes: Dict[str, ComparacaoComponente] = Field(default_factory=dict)
    componentes_com_status_concordante: List[str] = Field(default_factory=list)
    componentes_com_status_divergente: List[str] = Field(default_factory=list)
    alertas_gerais: List[str] = Field(default_factory=list)
    validacao_profissional_necessaria: bool = True
    componentes_com_divergencia_descritiva: List[str] = Field(default_factory=list)
    componentes_com_concordancia_descritiva: List[str] = Field(default_factory=list)
    componentes_com_comparacao_inconclusiva: List[str] = Field(default_factory=list)
    total_divergencias_descritivas: int = 0
    observacao_metodologica: str = (
        "A concordância de status mede apenas igualdade de avaliabilidade. "
        "As divergências descritivas são alertas lexicais sobre aspectos visuais "
        "possivelmente incompatíveis; qualificadores, regiões diferentes e contexto "
        "podem alterar sua interpretação. A ausência de alerta não comprova "
        "concordância semântica ou precisão clínica. Revisão profissional obrigatória."
    )

def _texto_lista(valores: Any) -> List[str]:
    return [str(v).strip() for v in valores if v is not None and str(v).strip()] if isinstance(valores, (list, tuple)) else []

def _ordem_provedores(nomes: List[str]) -> List[str]:
    return [n for n in ORDEM_PROVEDORES if n in nomes] + sorted(n for n in nomes if n not in ORDEM_PROVEDORES)

def _alertas_componente(relatorio: RelatorioValidacao, componente: str) -> List[str]:
    return [f"[{a.codigo}] {a.mensagem}" for a in relatorio.alertas if a.componente == componente]

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())

# Padrões intencionalmente restritos ao aspecto visual, e não à umidade real,
# viabilidade do tecido ou infecção. Pares são contrastes a revisar, não diagnósticos.
REGRAS = {
    "M": [dict(codigo="UMIDADE_SUPERFICIAL", caracteristica="Aparência de umidade superficial",
        a="aparentemente_seca", b="aparentemente_umida",
        pa=[r"\b(?:aparencia|aspecto|superficie|cobertura|camada)\s+(?:(?:visual|predominantemente|aparentemente|relativamente|mais)\s+)*(?:sec[ao]s?|ressecad[ao]s?)\b",
            r"\b(?:predominantemente|aparentemente)\s+sec[ao]s?\b"],
        pb=[r"\b(?:aparencia|aspecto|superficie|cobertura|camada)\s+(?:(?:visual|predominantemente|aparentemente|relativamente|mais)\s+)*(?:umid[ao]s?|molhad[ao]s?)\b",
            r"\b(?:predominantemente|aparentemente)\s+umid[ao]s?\b"] )],
    "E": [
        dict(codigo="BORDAS_REGULARIDADE", caracteristica="Regularidade das bordas",
             a="regular", b="irregular",
             pa=[r"\b(?:bordas?|contorno|margens?)\s+(?:(?:com|de|aspecto|relativamente|predominantemente|aparentemente)\s+)*(?:regular(?:es)?|uniforme(?:s)?)\b",
                 r"\b(?:relativamente|predominantemente)\s+regular(?:es)?\b"],
             pb=[r"\b(?:bordas?|contorno|margens?|transicao)\s+(?:(?:com|de|aspecto|relativamente|predominantemente)\s+)*(?:irregular(?:es)?|nao uniforme(?:s)?)\b",
                 r"\b(?:bordas?|contorno|margens?)\b[^.;]{0,45}\birregular(?:es)?\b"]),
        dict(codigo="BORDAS_DELIMITACAO", caracteristica="Delimitação das bordas",
             a="bem_delimitada", b="mal_delimitada",
             pa=[r"\b(?:bordas?|contorno|margens?)\s+(?:(?:bem|relativamente|claramente)\s+)?(?:definid[ao]s?|delimitad[ao]s?|nitid[ao]s?|demarcad[ao]s?)\b",
                 r"\bcontorno\s+(?:bem\s+)?definido\b"],
             pb=[r"\b(?:bordas?|contorno|margens?)\s+(?:(?:mal|pouco)\s+)(?:definid[ao]s?|delimitad[ao]s?)\b",
                 r"\b(?:bordas?|contorno|margens?)\s+(?:indistint[ao]s?|difus[ao]s?)\b"]),
    ],
    "S": [dict(codigo="DESCAMACAO_PELE", caracteristica="Descamação da pele ao redor",
               a="descamacao_descrita", b="ausencia_descamacao_descrita",
               pa=[r"\b(?:com|apresenta|presenca de|observa se)\s+(?:leve\s+)?descamacao\b", r"\bdescamacao\s+(?:superficial|visivel)\b"],
               pb=[r"\b(?:sem|ausencia de|nao apresenta)\s+descamacao\b"])],
}

# Negação explícita precisa ser reconhecida na oração da própria ocorrência.
NEGACAO = re.compile(r"\b(?:nao|sem|ausencia de|inexistencia de)\b")

def _segmentos(textos: List[str]) -> List[Tuple[str, str]]:
    saida = []
    for original in textos:
        for frase in re.split(r"(?<=[.!?;])\s+", original):
            if frase.strip():
                saida.append((frase.strip(), _normalizar(frase)))
    return saida

def _encontrar(textos: List[str], padroes: List[str], *, permitir_negacao: bool = False) -> Optional[str]:
    for original, normalizado in _segmentos(textos):
        for padrao in padroes:
            for achado in re.finditer(padrao, normalizado):
                prefixo = re.split(r"[,;:.]", normalizado[:achado.start()])[-1]
                # Negação na janela imediata evita 'não apresenta bordas regulares'.
                if not permitir_negacao and NEGACAO.search(prefixo[-38:]):
                    continue
                return original
    return None

def _classificar(textos: List[str], regra: dict) -> Optional[Tuple[str, str]]:
    # Evita falso positivo: 'irregulares' contém 'regulares' como substring,
    # mas os padrões usam fronteiras de palavra.
    a = _encontrar(textos, regra["pa"], permitir_negacao=regra["codigo"] == "DESCAMACAO_PELE" and False)
    b = _encontrar(textos, regra["pb"], permitir_negacao=regra["codigo"] == "DESCAMACAO_PELE")
    if bool(a) == bool(b):
        return None
    return (regra["a"], a) if a else (regra["b"], b)

def _textos_visuais(resposta: Any, letra: str, observacoes: List[str]) -> List[str]:
    textos = list(observacoes)
    nomes = {"E": {"bordas"}, "S": {"pele ao redor"}, "T": {"leito"}}.get(letra, set())
    for visual in resposta.caracteristicas_visuais:
        if _normalizar(visual.caracteristica) in nomes and visual.status != "nao_avaliavel" and visual.descricao:
            textos.append(visual.descricao.strip())
    return list(dict.fromkeys(textos))

def _comparar_descricoes(componente: ComparacaoComponente, respostas: dict) -> None:
    if len(componente.observacoes_por_provedor) < 2:
        componente.observacao_descritiva = "Menos de dois provedores com observações disponíveis."
        return
    encontrou_compatibilidade = False
    for regra in REGRAS.get(componente.componente, []):
        evidencias = []
        for nome, obs in componente.observacoes_por_provedor.items():
            textos = _textos_visuais(respostas[nome][0], componente.componente, obs.observacoes_visuais)
            achado = _classificar(textos, regra)
            if achado:
                evidencias.append(EvidenciaDescritiva(provedor=nome, valor_identificado=achado[0], trecho_original=achado[1]))
        if len(evidencias) < 2:
            continue
        componente.caracteristicas_comparadas.append(regra["caracteristica"])
        if len({e.valor_identificado for e in evidencias}) == 1:
            encontrou_compatibilidade = True
            continue
        descricao = f"Descrições potencialmente incompatíveis sobre {regra['caracteristica'].lower()}."
        componente.divergencias_descritivas.append(DivergenciaDescritiva(
            codigo=regra["codigo"], componente=componente.componente,
            caracteristica=regra["caracteristica"], descricao=descricao, evidencias=evidencias))
        componente.pontos_para_revisao.append(
            f"[{regra['codigo']}] {descricao} " + "; ".join(f"{e.provedor}: {e.valor_identificado}" for e in evidencias)
            + ". Conferir as descrições originais e a região observada com o profissional.")
    componente.divergencia_descritiva = bool(componente.divergencias_descritivas)
    if componente.divergencia_descritiva:
        componente.situacao_descritiva = "divergente"
        componente.observacao_descritiva = "Contrastes lexicais identificados; exigem revisão contextual e profissional."
    elif encontrou_compatibilidade:
        componente.situacao_descritiva = "concordante_parcial"
        componente.observacao_descritiva = "Descrições compatíveis em características específicas; não comprova concordância completa."
    else:
        componente.situacao_descritiva = "inconclusiva"
        componente.observacao_descritiva = "Evidências insuficientes nas regras disponíveis; não significa concordância ou discordância."

def comparar_resultados(
    resultado: ResultadoAnaliseMultimodal,
    relatorios_validacao: Optional[Dict[str, RelatorioValidacao]] = None,
) -> ResultadoComparacao:
    comparacao = ResultadoComparacao()
    relatorios = relatorios_validacao if relatorios_validacao is not None else {}
    respostas = {}
    for nome in _ordem_provedores(list(resultado.resultados.keys())):
        provedor = resultado.resultados[nome]
        if not (provedor.sucesso and provedor.resposta is not None):
            comparacao.provedores_indisponiveis.append(nome)
            comparacao.resumos_provedores[nome] = ResumoProvedor(
                provedor=nome, sucesso=False, tempo_execucao_segundos=provedor.tempo_execucao_segundos,
                mensagem_erro=provedor.mensagem_erro)
            continue
        resposta = provedor.resposta
        relatorio = relatorios.get(nome)
        if relatorio is None:
            relatorio = validar_resposta(resposta)
        respostas[nome] = (resposta, relatorio)
        comparacao.provedores_comparados.append(nome)
        comparacao.resumos_provedores[nome] = ResumoProvedor(
            provedor=nome, sucesso=True, tempo_execucao_segundos=provedor.tempo_execucao_segundos,
            status_resposta=resposta.status_resposta, valido_estruturalmente=relatorio.valido_estruturalmente,
            quantidade_alertas=relatorio.total_alertas)
        for alerta in relatorio.alertas:
            if alerta.componente is None:
                comparacao.alertas_gerais.append(f"{nome}: [{alerta.codigo}] {alerta.mensagem}")
    for letra, nome_componente in COMPONENTES_TIMES.items():
        componente = ComparacaoComponente(componente=letra, nome=nome_componente)
        status_encontrados = []
        for nome, (resposta, relatorio) in respostas.items():
            item = next((i for i in resposta.avaliacao_times if i.componente == letra), None)
            if item is None:
                componente.pontos_para_revisao.append(f"{nome}: componente {letra} não encontrado.")
                continue
            status_encontrados.append(item.status)
            alertas = _alertas_componente(relatorio, letra)
            componente.observacoes_por_provedor[nome] = ObservacaoProvedor(
                provedor=nome, status=item.status, observacoes_visuais=_texto_lista(item.observacoes_visuais),
                dados_clinicos_relacionados=_texto_lista(item.dados_clinicos_relacionados),
                informacoes_pendentes=_texto_lista(item.informacoes_pendentes), limitacoes=_texto_lista(item.limitacoes),
                quantidade_alertas=len(alertas), alertas=alertas)
        componente.status_identificados = sorted(set(status_encontrados))
        componente.concordancia_status = len(status_encontrados) >= 2 and len(set(status_encontrados)) == 1
        componente.divergencia_status = len(set(status_encontrados)) > 1
        if componente.divergencia_status:
            resumo = ", ".join(f"{n}: {o.status}" for n, o in componente.observacoes_por_provedor.items())
            componente.pontos_para_revisao.append("Divergência de status entre modelos: " + resumo)
            comparacao.componentes_com_status_divergente.append(letra)
        elif componente.concordancia_status:
            comparacao.componentes_com_status_concordante.append(letra)
        _comparar_descricoes(componente, respostas)
        if componente.divergencia_descritiva:
            comparacao.componentes_com_divergencia_descritiva.append(letra)
            comparacao.total_divergencias_descritivas += len(componente.divergencias_descritivas)
        elif componente.situacao_descritiva == "concordante_parcial":
            comparacao.componentes_com_concordancia_descritiva.append(letra)
        else:
            comparacao.componentes_com_comparacao_inconclusiva.append(letra)
        comparacao.componentes[letra] = componente
    if len(comparacao.provedores_comparados) < 2:
        comparacao.alertas_gerais.append("Menos de dois provedores disponíveis. Não é possível estabelecer concordância entre modelos.")
    if comparacao.total_divergencias_descritivas:
        comparacao.alertas_gerais.append(
            f"Foram identificadas {comparacao.total_divergencias_descritivas} divergência(s) descritiva(s) potencial(is). "
            "Verificar os trechos originais com o profissional.")
    return comparacao
