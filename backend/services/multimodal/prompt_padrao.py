
import json
import logging
from typing import Any

from schemas.multimodal import (
    AnaliseMultimodalInput,
    RespostaEstruturadaModelo,
    AvaliacaoComponenteTimestamps,
    ObservacaoVisual,
    CaracterizacaoTecido,
)

logger = logging.getLogger(__name__)

NOMES = {
    "T": "Tecido",
    "I": "Inflamação/infecção",
    "M": "Umidade",
    "E": "Bordas",
    "S": "Pele ao redor",
}

STATUS_VALIDOS = {
    "avaliavel",
    "parcialmente_avaliavel",
    "nao_avaliavel",
}


def _lista_textos(valor: Any, limite: int = 10) -> list[str]:
    if not isinstance(valor, list):
        return []

    resultado = []
    vistos = set()

    for item in valor:
        if not isinstance(item, str):
            continue

        texto = item.strip()

        if not texto:
            continue

        chave = texto.casefold()

        if chave in vistos:
            continue

        vistos.add(chave)
        resultado.append(texto)

        if len(resultado) >= limite:
            break

    return resultado


def _status(
    valor: Any,
    padrao: str = "parcialmente_avaliavel",
) -> str:
    if isinstance(valor, str) and valor in STATUS_VALIDOS:
        return valor

    return padrao


def construir_prompt(
    entrada: AnaliseMultimodalInput,
) -> str:

    dados = entrada.dados_clinicos.model_dump(
        mode="json"
    )

    estrutura = {
        "descricao": "",
        "qualidade": "parcialmente_avaliavel",
        "limitacoes": [],
        "caracteristicas": [
            {
                "nome": "cor",
                "descricao": "",
                "status": "nao_avaliavel",
            },
            {
                "nome": "bordas",
                "descricao": "",
                "status": "nao_avaliavel",
            },
            {
                "nome": "leito",
                "descricao": "",
                "status": "nao_avaliavel",
            },
            {
                "nome": "pele ao redor",
                "descricao": "",
                "status": "nao_avaliavel",
            },
        ],
        "times": {
            letra: {
                "status": "nao_avaliavel",
                "observacoes": [],
                "pendencias": [],
                "limitacoes": [],
            }
            for letra in NOMES
        },
        "aparencias_tecidos": [],
        "pontos_revisao": [],
    }

    return f"""
SISTEMA: AVALIA & TRATA
MÓDULO: ANÁLISE MULTIMODAL DE LESÕES CUTÂNEAS

PAPEL:
Você atua como assistente de documentação visual
para um sistema de apoio ao trabalho de enfermagem.

Sua tarefa é interpretar uma fotografia de lesão
cutânea juntamente com informações fornecidas
pelo profissional e produzir uma resposta estruturada
para revisão, edição e validação do enfermeiro.

Você NÃO realiza diagnóstico, não define tratamento
e não substitui a avaliação presencial.

OBJETIVO DA ANÁLISE:

1. Descrever características visualmente observáveis.
2. Organizar os achados pelo método T.I.M.E.S.
3. Relacionar dados clínicos informados quando pertinentes.
4. Identificar o que não pode ser avaliado.
5. Produzir dados úteis para comparação e acompanhamento.
6. Evitar contradições entre as seções da resposta.

==================================================
A. REGRAS DE SEGURANÇA E FIDELIDADE
==================================================

A1. Use a fotografia apenas para descrever aparência
visual, sem apresentar hipóteses como fatos confirmados.

A2. Não confirme infecção, biofilme, necrose,
profundidade, viabilidade tecidual ou etiologia
exclusivamente pela imagem.

A3. Não determine uma fase de cicatrização como
conclusão clínica a partir de uma fotografia isolada.

A4. Não prescreva medicamentos, coberturas,
desbridamento ou outros procedimentos.

A5. Não recomende manipular ou remover material
visível na lesão a partir da fotografia.

A6. Não invente resultados de palpação, temperatura,
sensibilidade, perfusão, odor, dor ou exames.

A7. Não presuma ausência de infecção por não haver
sinais evidentes na imagem.

A8. Não invente medidas, percentuais teciduais,
áreas físicas, coordenadas ou polígonos.

A9. Não atribua comorbidades, histórico clínico
ou causas que não tenham sido fornecidos.

A10. Não apresente uma fotografia como suficiente
para confirmar qualquer classificação clínica.

A11. Dados clínicos ausentes devem permanecer
desconhecidos, nunca tratados como negativos.

A12. Não repita exemplos ou instruções deste prompt
como se fossem observações da imagem.

==================================================
B. FONTES DAS INFORMAÇÕES
==================================================

Considere três categorias distintas:

1. OBSERVAÇÃO VISUAL
Informação diretamente perceptível na fotografia.

2. DADO CLÍNICO INFORMADO
Informação fornecida explicitamente pelo profissional.

3. INFORMAÇÃO PENDENTE
Dado que depende de confirmação clínica,
exame presencial ou informação adicional.

Não misture essas categorias.

A localização e as medidas fornecidas são dados
do profissional, não resultados de mensuração por IA.

Não declare que um dado clínico foi observado
na fotografia quando ele apenas foi informado.

==================================================
C. DESCRIÇÃO GERAL
==================================================

Preencha "descricao" com duas a quatro frases.

A descrição deve priorizar, quando visíveis:

- localização informada da lesão;
- aspecto geral da superfície;
- colorações observáveis;
- configuração das bordas;
- características da pele ao redor.

Use linguagem objetiva e específica.

Evite afirmações vagas como:
"apresenta características de ferida"
ou "necessita de avaliação médica".

Se a visualização do leito for limitada,
explique diretamente o motivo aparente.

Não utilize "normal", "saudável", "infectado"
ou "necrótico" como classificações definitivas
derivadas apenas da imagem.

==================================================
D. QUALIDADE DA IMAGEM
==================================================

Preencha "qualidade" com exatamente um valor:

"avaliavel"
"parcialmente_avaliavel"
"nao_avaliavel"

A qualidade deve refletir a capacidade de
descrever características, e não a gravidade clínica.

Em "limitacoes", inclua apenas limitações
realmente identificáveis, como:

- desfoque;
- iluminação insuficiente;
- reflexos importantes;
- enquadramento inadequado;
- obstrução da região de interesse;
- ausência de escala para medição física;
- impossibilidade de observar estruturas encobertas.

Não invente problemas de qualidade.

Uma imagem pode permitir avaliar bordas
e pele ao redor mesmo quando o leito
não estiver diretamente visível.

==================================================
E. CARACTERÍSTICAS VISUAIS
==================================================

Retorne exatamente quatro objetos em
"caracteristicas", com os seguintes nomes:

"cor"
"bordas"
"leito"
"pele ao redor"

Cada objeto deve incluir:

"nome"
"descricao"
"status"

Para "status", utilize um dos três estados válidos.

COR:
Descreva tonalidades e sua distribuição visível.
Não transforme cor em diagnóstico de tecido.

BORDAS:
Descreva delimitação, contorno, regularidade
e transição visual para a pele circundante.

LEITO:
Descreva apenas o que estiver visível
na superfície ou no leito da lesão.
Se estiver encoberto, registre essa limitação.

PELE AO REDOR:
Descreva características superficiais visíveis
na pele adjacente, quando houver.

Quando não for possível avaliar um item:
- use status "nao_avaliavel";
- explique brevemente a limitação;
- não invente observações para preencher o campo.

==================================================
F. AVALIAÇÃO T.I.M.E.S.
==================================================

Preencha obrigatoriamente os cinco componentes:
T, I, M, E e S.

Cada componente deve ter:

"status"
"observacoes"
"pendencias"
"limitacoes"

OBSERVACOES:
Somente achados visuais pertinentes ao componente.

PENDENCIAS:
Informações que o profissional precisa confirmar
para completar aquele componente.

LIMITACOES:
Restrições da fotografia que impedem a avaliação.

Não coloque uma informação na categoria errada.

-----------------------------------------
T — TECIDO / SUPERFÍCIE DA LESÃO
-----------------------------------------

Foco: aparência visual da superfície e do leito.

Pode descrever:
- tonalidades da superfície;
- textura aparentemente visível;
- cobertura superficial;
- áreas visualmente distintas;
- obstrução da visualização do leito.

Não confirme o tipo histológico do tecido.

Não determine percentuais de granulação,
esfacelo, necrose ou epitelização.

Se uma cobertura impedir visualizar o leito,
registre a cobertura como aparência superficial
e explique que o leito não está visível.

Não marque T como "nao_avaliavel" apenas porque
não é possível identificar o tipo de tecido,
quando sua aparência superficial for descritível.

-----------------------------------------
I — INFLAMAÇÃO / INFECÇÃO
-----------------------------------------

Foco: alterações visualmente observáveis
que possam orientar a revisão profissional.

Pode descrever:
- alterações aparentes de coloração;
- diferenças visuais na região adjacente;
- outros sinais superficiais efetivamente visíveis.

Não diagnostique infecção ou inflamação clínica.

Não afirme ausência de infecção.

Dor, calor, odor, sinais sistêmicos e informações
não visíveis pertencem aos dados fornecidos
ou às pendências para avaliação presencial.

Não transfira automaticamente toda alteração
de coloração para um diagnóstico inflamatório.

-----------------------------------------
M — UMIDADE / EXSUDATO
-----------------------------------------

Foco: condições visíveis de umidade.

Pode descrever:
- aspecto aparentemente seco ou úmido;
- brilho superficial;
- presença de líquido visível;
- distribuição de umidade observável.

Não declare exsudato quando não for identificável.

Não determine tipo, volume ou origem do exsudato
sem dados suficientes.

Se o profissional informou tipo de exsudato,
esse dado é clínico informado, e não
observação visual produzida pela IA.

Não coloque neste componente recomendações
de remoção de tecido, avaliação de viabilidade
ou caracterização histológica.

-----------------------------------------
E — BORDAS / AVANÇO EPITELIAL
-----------------------------------------

Foco: características das bordas da lesão.

Pode descrever:
- regularidade do contorno;
- delimitação;
- aspecto aparente da transição;
- áreas de borda encobertas ou pouco visíveis;
- características de superfície junto à margem.

Uma única fotografia não estabelece
a velocidade do avanço epitelial.

Não determine se houve progressão temporal
sem fotografias anteriores comparáveis.

Não use E para analisar volume ou tipo
de exsudato.

Se as bordas foram descritas em
"caracteristicas", devem aparecer também
nas observações do componente E,
quando houver observação efetiva.

-----------------------------------------
S — PELE AO REDOR
-----------------------------------------

Foco: pele perilesional.

Pode descrever:
- tonalidade;
- textura;
- descamação;
- alterações superficiais visíveis;
- aspecto seco ou úmido na pele adjacente.

Não conclua perfusão, neuropatia,
etiologia ou sensibilidade pela imagem.

Se houver descrição relevante da pele ao redor
em "caracteristicas", registre a mesma
observação no componente S.

Não marque S como "nao_avaliavel" se a pele
circundante estiver visível e descritível.

==================================================
G. CONSISTÊNCIA ENTRE OS CAMPOS
==================================================

Esta etapa é obrigatória antes de responder.

G1. Toda característica de borda que apareça
na descrição visual deve estar coerente com E.

G2. Toda observação relevante da pele ao redor
deve estar coerente com S.

G3. Toda descrição da aparência do leito ou
da superfície deve estar coerente com T.

G4. Observações sobre umidade ou líquido visível
devem estar coerentes com M.

G5. Observações visuais em I não devem
ser transformadas em diagnóstico de infecção.

G6. Não declare um componente "nao_avaliavel"
se houver achado visual válido registrado
nas observações daquele componente.

G7. Não deixe "observacoes" vazia em E ou S
quando você descreveu características visíveis
correspondentes em "caracteristicas".

G8. Se não for possível fazer uma observação,
não copie uma pendência para "observacoes".

G9. Não repita a mesma frase genérica em todos
os componentes para parecer que a análise
está completa.

G10. Não force os cinco componentes a terem
observações. Um campo vazio é preferível
a um achado inventado.

==================================================
H. APARÊNCIAS DE TECIDOS
==================================================

Preencha "aparencias_tecidos" apenas quando
existirem características de superfície
suficientemente visíveis para uma descrição.

Cada objeto contém:

"aparencia"
"justificativa"

"Aparencia" é a descrição visual,
não uma classificação confirmada.

"Justificativa" explica a limitação
da interpretação.

Não atribua percentuais.

Não identifique como granulação, necrose,
esfacelo ou epitelização confirmados
somente pela fotografia.

Quando não houver descrição confiável,
retorne uma lista vazia.

==================================================
I. PONTOS PARA REVISÃO PROFISSIONAL
==================================================

Preencha "pontos_revisao" com questões
concretas e relevantes para esta avaliação.

Priorize informações não fornecidas que
possam melhorar a documentação.

Evite perguntas genéricas ou repetidas.

Não prescreva tratamentos.

Não solicite procedimentos invasivos.

Não transforme hipóteses em fatos clínicos.

==================================================
J. ESTRUTURA JSON OBRIGATÓRIA
==================================================

Responda exclusivamente com este formato:

{json.dumps(estrutura, ensure_ascii=False, indent=2)}

ATENÇÃO SOBRE O MODELO:

- Os valores vazios são apenas placeholders.
- Preencha conforme a fotografia.
- Não copie o conteúdo dos exemplos.
- Use somente as chaves indicadas.
- Não omita T, I, M, E ou S.
- Não acrescente texto fora do JSON.
- Não use comentários ou Markdown.
- Todas as listas devem ser arrays JSON.
- Os status devem seguir os valores permitidos.
- Garanta que o JSON esteja completo e válido.

==================================================
K. DADOS INFORMADOS PELO PROFISSIONAL
==================================================

{json.dumps(dados, ensure_ascii=False, indent=2)}

Esses dados são informações fornecidas.
Não suponha dados clínicos adicionais.

==================================================
L. VERIFICAÇÃO FINAL ANTES DA RESPOSTA
==================================================

Verifique internamente:

1. JSON sintaticamente válido.
2. Os cinco componentes T.I.M.E.S. presentes.
3. Cada componente com classificação adequada.
4. Bordas coerentes entre características e E.
5. Pele ao redor coerente entre características e S.
6. Nenhuma observação clínica inventada.
7. Nenhum diagnóstico definitivo pela fotografia.
8. Nenhuma prescrição ou procedimento recomendado.
9. Nenhum percentual ou medida inventada.
10. Campos desconhecidos tratados como desconhecidos.

Retorne somente o JSON.
""".strip()


def normalizar_resposta(
    dados: dict,
    entrada: AnaliseMultimodalInput,
) -> RespostaEstruturadaModelo:

    if not isinstance(dados, dict):
        raise ValueError(
            "Resposta da IA não é um objeto JSON."
        )

    descricao = dados.get("descricao")

    if (
        not isinstance(descricao, str)
        or not descricao.strip()
    ):
        raise ValueError(
            "JSON sem campo descricao válido."
        )

    times = dados.get("times")

    if not isinstance(times, dict):
        raise ValueError(
            "JSON sem objeto times válido."
        )

    faltantes = [
        letra
        for letra in NOMES
        if not isinstance(times.get(letra), dict)
    ]

    if faltantes:
        raise ValueError(
            "Componentes T.I.M.E.S. ausentes: "
            + ", ".join(faltantes)
        )

    r = RespostaEstruturadaModelo()

    r.conteudo_descricao = descricao.strip()

    r.limitacoes_declaradas = _lista_textos(
        dados.get("limitacoes")
    )

    r.qualidade_imagem.status = _status(
        dados.get("qualidade"),
        "parcialmente_avaliavel",
    )

    r.qualidade_imagem.limitacoes = list(
        r.limitacoes_declaradas
    )

    # CARACTERÍSTICAS VISUAIS

    caracteristicas = dados.get(
        "caracteristicas",
        []
    )

    if not isinstance(caracteristicas, list):
        caracteristicas = []

    por_nome = {}

    for item in caracteristicas:
        if not isinstance(item, dict):
            continue

        nome = item.get("nome")
        texto = item.get("descricao")

        if not isinstance(nome, str):
            continue

        if not isinstance(texto, str):
            continue

        nome = nome.strip().lower()
        texto = texto.strip()

        if not nome or not texto:
            continue

        status = _status(
            item.get("status"),
            "parcialmente_avaliavel",
        )

        r.caracteristicas_visuais.append(
            ObservacaoVisual(
                caracteristica=nome,
                descricao=texto,
                status=status,
            )
        )

        por_nome[nome] = {
            "descricao": texto,
            "status": status,
        }

    # COMPONENTES T.I.M.E.S.

    por_componente = {}

    for letra, nome in NOMES.items():
        item = times[letra]

        observacoes = _lista_textos(
            item.get("observacoes")
        )

        pendencias = _lista_textos(
            item.get("pendencias")
        )

        limitacoes = _lista_textos(
            item.get("limitacoes")
        )

        if observacoes:
            status = _status(
                item.get("status"),
                "parcialmente_avaliavel",
            )

            if status == "nao_avaliavel":
                status = "parcialmente_avaliavel"

        else:
            status = "nao_avaliavel"

        if not observacoes and not pendencias:
            pendencias = [
                "Completar avaliação presencial "
                "deste componente."
            ]

        componente = AvaliacaoComponenteTimestamps(
            componente=letra,
            nome=nome,
            status=status,
            observacoes_visuais=observacoes,
            informacoes_pendentes=pendencias,
            limitacoes=limitacoes,
        )

        r.avaliacao_times.append(componente)
        por_componente[letra] = componente

    # DADOS CLÍNICOS RELACIONADOS
    # Apenas informações efetivamente fornecidas.

    clinicos = entrada.dados_clinicos

    if clinicos.tipoExsudato:
        por_componente[
            "M"
        ].dados_clinicos_relacionados.append(
            "Tipo de exsudato informado: "
            + clinicos.tipoExsudato
        )

    if clinicos.odor is not None:
        por_componente[
            "I"
        ].dados_clinicos_relacionados.append(
            "Odor informado: "
            + ("sim" if clinicos.odor else "não")
        )

    if clinicos.nivelDor:
        por_componente[
            "I"
        ].dados_clinicos_relacionados.append(
            "Nível de dor informado: "
            + clinicos.nivelDor
        )

    # AVISOS DE COERÊNCIA
    # Não inventar observações para resolver
    # contradições do modelo.

    avisos = []

    correspondencias = {
        "bordas": "E",
        "pele ao redor": "S",
        "leito": "T",
    }

    for nome_visual, letra in correspondencias.items():
        visual = por_nome.get(nome_visual)
        componente = por_componente[letra]

        if (
            visual
            and visual["status"] != "nao_avaliavel"
            and not componente.observacoes_visuais
        ):
            aviso = (
                f"Inconsistência para revisão: "
                f"'{nome_visual}' possui descrição "
                f"visual, mas o componente "
                f"{letra} não possui observações."
            )

            avisos.append(aviso)
            logger.warning(aviso)

    # APARÊNCIAS DE TECIDOS

    aparencias = dados.get(
        "aparencias_tecidos",
        []
    )

    if not isinstance(aparencias, list):
        aparencias = []

    for item in aparencias:
        if not isinstance(item, dict):
            continue

        aparencia = item.get("aparencia")

        if (
            not isinstance(aparencia, str)
            or not aparencia.strip()
        ):
            continue

        justificativa = item.get("justificativa")

        if not isinstance(justificativa, str):
            justificativa = (
                "A fotografia não permite "
                "confirmar o tipo de tecido."
            )

        r.avaliacao_tecidos.tecidos.append(
            CaracterizacaoTecido(
                tipo="aparencia_visual_nao_confirmada",
                descricao_visual=aparencia.strip(),
                justificativa=justificativa.strip(),
                percentual_estimado=None,
                revisao_profissional_necessaria=True,
            )
        )

    r.avaliacao_tecidos.status = (
        "parcialmente_avaliavel"
        if r.avaliacao_tecidos.tecidos
        else "nao_avaliavel"
    )

    r.avaliacao_tecidos.limitacoes = [
        "A aparência não confirma o tipo de tecido; "
        "requer avaliação profissional.",
        "Percentuais não calculados sem "
        "segmentação validada.",
    ]

    # MARCAÇÕES
    # Esta etapa deverá ser implementada por
    # módulo de segmentação separado e validado.

    r.marcacoes_imagem.limitacoes = [
        "Não foram gerados polígonos nesta etapa. "
        "Marcações exigem segmentação e "
        "conferência profissional."
    ]

    # PONTOS PARA REVISÃO PROFISSIONAL

    r.pontos_para_revisao_profissional = (
        _lista_textos(
            dados.get("pontos_revisao")
        )
    )

    r.pontos_para_revisao_profissional.extend(
        avisos
    )

    if not r.pontos_para_revisao_profissional:
        r.pontos_para_revisao_profissional = [
            "Conferir os achados visuais e "
            "completar os dados clínicos."
        ]

    # PRESERVAR DADOS ORIGINAIS

    d = entrada.dados_clinicos

    r.dados_clinicos_organizados.localizacao = (
        d.localizacao
    )

    campos = [
        ("comprimento", "comprimento"),
        ("largura", "largura"),
        ("tipoExsudato", "tipo_exsudato"),
        ("odor", "odor"),
        ("nivelDor", "nivel_dor"),
        ("queixaPrincipal", "queixa_principal"),
        ("observacoes", "observacoes"),
    ]

    for origem, destino in campos:
        valor = getattr(d, origem)

        setattr(
            r.dados_clinicos_organizados,
            destino,
            valor,
        )

        if valor is None or valor == "":
            r.dados_clinicos_organizados.dados_nao_informados.append(
                destino
            )

    # MEDIDAS
    # Preservam-se os valores do profissional,
    # sem inferir área real pela fotografia.

    r.medidas.comprimento_informado_cm = (
        d.comprimento
    )

    r.medidas.largura_informada_cm = (
        d.largura
    )

    r.medidas.observacoes = [
        "Comprimento e largura informados "
        "pelo profissional; área não calculada "
        "sem método validado."
    ]

    return r
