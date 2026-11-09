"""Testes offline da Etapa 2G, sem pacientes e sem chamadas externas."""
import cv2
import numpy as np

from schemas.multimodal import AnaliseMultimodalInput, AnaliseTecnicaOpenCVInput, DadosClinicosInput
from services.multimodal.prompt_padrao import construir_prompt, normalizar_resposta
from services.multimodal.validacao_regioes import validar_regioes_propostas
from services.propostas_tecidos import regioes_para_editor, detalhes_propostas
from services.visualizacao_marcacoes import VisualizacaoMarcacoesService, validar_regioes_persistidas
from services.segmentacao_profissional import gerar_visualizacao
from schemas.revisao_marcacoes import RegiaoManual


def pontos():
    return [{'x': .2, 'y': .2}, {'x': .65, 'y': .2}, {'x': .65, 'y': .65}, {'x': .2, 'y': .65}]


def proposta(tipo='superficie_avermelhada', classe='granulacao', **kwargs):
    dado = {
        'tipo_regiao': tipo,
        'descricao': 'Área de teste sintética',
        'confianca': 'moderada',
        'pontos': pontos(),
        'classificacao_tecido_proposta': classe,
        'justificativa_classificacao': 'Textura e relevo da superfície distinguíveis em região de teste.',
        'confianca_classificacao': 'moderada',
    }
    dado.update(kwargs)
    return dado


def test_proposta_independente_da_cor_e_persistencia_no_json():
    regioes, _ = validar_regioes_propostas([proposta(tipo='superficie_amarelada', classe='granulacao')])
    assert len(regioes) == 1
    assert regioes[0].classificacao_tecido_proposta == 'granulacao'
    assert regioes[0].revisao_profissional_necessaria
    assert 'granulacao' in regioes[0].model_dump_json()
    convertido = regioes_para_editor(regioes, 'gemini')[0]
    assert convertido['classe'] == 'granulacao'
    assert convertido['classe_proposta_ia'] == 'granulacao'
    assert convertido['origem'] == 'ia'
    assert detalhes_propostas(regioes)[0]['classificacao_proposta'] == 'granulacao'
    assert RegiaoManual.model_validate(convertido).classe_proposta_ia == 'granulacao'


def test_cor_isolada_nao_gera_classificacao():
    regioes, _ = validar_regioes_propostas([proposta(classe='necrose', justificativa_classificacao='escura')])
    assert regioes[0].classificacao_tecido_proposta == 'nao_classificado'
    assert regioes_para_editor(regioes, 'kimi')[0]['classe'] == 'nao_classificado'


def test_baixa_confianca_downgrade_sem_descartar_poligono():
    regioes, _ = validar_regioes_propostas([proposta(classe='esfacelo', confianca_classificacao='baixa')])
    assert len(regioes) == 1
    assert regioes[0].classificacao_tecido_proposta == 'nao_classificado'


def test_tipo_visual_nao_e_classificacao_de_tecido():
    regioes, _ = validar_regioes_propostas([proposta(tipo='contorno_visual_lesao', classe='necrose')])
    assert regioes[0].classificacao_tecido_proposta == 'nao_classificado'
    assert regioes_para_editor(regioes, 'openai')[0]['classe'] == 'contorno_lesao'


def test_entrada_maliciosa_nao_interrompe_normalizacao():
    regioes, _ = validar_regioes_propostas([proposta(classe={'inventado': 'necrose'})])
    assert len(regioes) == 1
    assert regioes[0].classificacao_tecido_proposta == 'nao_classificado'


def test_revalidacao_downgrade_conteudo_persistido_adulterado():
    regioes, _ = validar_regioes_propostas([proposta()])
    dados = regioes[0].model_dump(mode='json')
    dados['justificativa_classificacao'] = 'cor'
    persistido = {'marcacoes_imagem': {'sistema_coordenadas': 'normalizado_0_1',
                                      'imagem_referencia': 'processada', 'regioes': [dados]}}
    recuperadas = validar_regioes_persistidas(persistido)
    assert len(recuperadas) == 1
    assert recuperadas[0].classificacao_tecido_proposta == 'nao_classificado'


def test_prompt_gemini_e_normalizador_mantem_times():
    entrada = AnaliseMultimodalInput(
        caminho_imagem_original='foto.png', caminho_imagem_processada='proc.png',
        dimensoes_originais={'largura': 400, 'altura': 400},
        dimensoes_processadas={'largura': 400, 'altura': 400},
        analise_tecnica=AnaliseTecnicaOpenCVInput(brilho_medio=90, contraste_global=55),
        dados_clinicos=DadosClinicosInput(localizacao='perna'),
    )
    prompt = construir_prompt(entrada)
    assert 'classificacao_tecido_proposta' in prompt
    assert 'nao_classificado' in prompt
    resultado = normalizar_resposta({
        'descricao': 'Descrição de teste',
        'times': {k: {'status': 'nao_avaliavel', 'observacoes': [], 'pendencias': [], 'limitacoes': []} for k in 'TIMES'},
        'regioes_propostas': [proposta()],
    }, entrada)
    assert len(resultado.avaliacao_times) == 5
    assert resultado.marcacoes_imagem.regioes[0].classificacao_tecido_proposta == 'granulacao'
    assert resultado.avaliacao_tecidos.tecidos == []  # não inventa percentuais


def test_imagem_ia_e_imagem_revisada_sao_separadas(tmp_path):
    origem = tmp_path / 'origem.png'
    ia = tmp_path / 'proposta.png'
    revisada = tmp_path / 'revisada.png'
    imagem = np.full((500, 500, 3), 150, dtype=np.uint8)
    cv2.imwrite(str(origem), imagem)
    regioes, _ = validar_regioes_propostas([proposta()])
    VisualizacaoMarcacoesService.gerar(str(origem), regioes, str(ia), 'gemini')
    manual = [RegiaoManual(id='m1', classe='granulacao', pontos=pontos(),
                           classe_proposta_ia='granulacao', origem='ia')]
    _, estatisticas = gerar_visualizacao(str(origem), manual, str(revisada), aprovado=False, provedor='gemini')
    assert estatisticas['status_validacao'] == 'rascunho_nao_validado'
    assert np.array_equal(cv2.imread(str(origem)), imagem)
    assert ia.exists() and revisada.exists()
    assert not np.array_equal(cv2.imread(str(ia)), cv2.imread(str(revisada)))
