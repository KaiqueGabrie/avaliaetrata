import json
from schemas.multimodal import AnaliseMultimodalInput, RespostaEstruturadaModelo, AvaliacaoComponenteTimestamps, ObservacaoVisual, CaracterizacaoTecido

NOMES = {'T':'Tecido','I':'Inflamação/infecção','M':'Umidade','E':'Bordas','S':'Pele ao redor'}

def construir_prompt(entrada: AnaliseMultimodalInput) -> str:
    dados = entrada.dados_clinicos.model_dump()
    return ('Analise a FOTO como apoio à documentação de feridas. Responda APENAS um objeto JSON em português, sem Markdown. '
      'Descreva observações visuais, não diagnósticos. Não confirme infecção, necrose, fase de cicatrização, profundidade ou tecido apenas pela foto. '
      'Não recomende procedimentos, medicamentos ou tratamentos. Não invente percentuais, coordenadas ou área física. '
      'JSON obrigatório com estas chaves: '
      '{"descricao":"descrição objetiva em 2-4 frases",'
      '"qualidade":"avaliavel ou parcialmente_avaliavel ou nao_avaliavel",'
      '"limitacoes":["limitação da imagem"],'
      '"caracteristicas":[{"nome":"cor/bordas/leito/pele ao redor","descricao":"observação"}],'
      '"times":{"T":{"observacoes":["..."],"pendencias":["..."]},'
      '"I":{"observacoes":[],"pendencias":[]},"M":{"observacoes":[],"pendencias":[]},'
      '"E":{"observacoes":[],"pendencias":[]},"S":{"observacoes":[],"pendencias":[]}},'
      '"aparencias_tecidos":[{"aparencia":"descrição visual sem confirmar tecido","justificativa":"..."}],'
      '"pontos_revisao":["questão para enfermeiro conferir"]}. '
      'Se não conseguir observar algo, deixe a observação vazia e explique a pendência. '
      'Não peça histologia rotineiramente para caracterização visual. '
      'Dados informados pelo profissional (não inferir outros): '+json.dumps(dados,ensure_ascii=False,separators=(',',':')))

def normalizar_resposta(dados: dict, entrada: AnaliseMultimodalInput) -> RespostaEstruturadaModelo:
    if not isinstance(dados, dict) or not isinstance(dados.get('descricao'),str) or not dados['descricao'].strip():
        raise ValueError('JSON sem campo descricao válido')
    r = RespostaEstruturadaModelo()
    r.conteudo_descricao = dados['descricao'].strip()
    r.limitacoes_declaradas = [str(x) for x in dados.get('limitacoes',[]) if isinstance(x,str)]
    status = dados.get('qualidade','parcialmente_avaliavel')
    r.qualidade_imagem.status = status if status in ('avaliavel','parcialmente_avaliavel','nao_avaliavel') else 'parcialmente_avaliavel'
    r.qualidade_imagem.limitacoes = list(r.limitacoes_declaradas)
    for item in dados.get('caracteristicas',[]):
        if isinstance(item,dict) and item.get('nome') and item.get('descricao'):
            r.caracteristicas_visuais.append(ObservacaoVisual(caracteristica=str(item['nome']),descricao=str(item['descricao']),status='avaliavel'))
    times = dados.get('times') or {}
    for letra,nome in NOMES.items():
        item = times.get(letra) or {}
        obs = [str(x) for x in item.get('observacoes',[]) if isinstance(x,str)] if isinstance(item,dict) else []
        pend = [str(x) for x in item.get('pendencias',[]) if isinstance(x,str)] if isinstance(item,dict) else []
        r.avaliacao_times.append(AvaliacaoComponenteTimestamps(componente=letra,nome=nome,status='parcialmente_avaliavel' if obs else 'nao_avaliavel',observacoes_visuais=obs,informacoes_pendentes=pend or ([] if obs else ['Confirmar na avaliação presencial.'])))
    for item in dados.get('aparencias_tecidos',[]):
        if isinstance(item,dict) and item.get('aparencia'):
            r.avaliacao_tecidos.tecidos.append(CaracterizacaoTecido(tipo='aparencia_visual_nao_confirmada',descricao_visual=str(item['aparencia']),justificativa=str(item.get('justificativa','Apenas aspecto fotográfico')),percentual_estimado=None))
    r.avaliacao_tecidos.status = 'parcialmente_avaliavel' if r.avaliacao_tecidos.tecidos else 'nao_avaliavel'
    r.avaliacao_tecidos.limitacoes = ['A aparência não confirma o tipo de tecido; requer avaliação profissional.','Percentuais não calculados sem segmentação validada.']
    r.marcacoes_imagem.limitacoes = ['Sem polígonos: a localização espacial exige segmentação e conferência profissional.']
    r.pontos_para_revisao_profissional = [str(x) for x in dados.get('pontos_revisao',[]) if isinstance(x,str)] or ['Conferir os achados visuais e completar os dados clínicos.']
    d=entrada.dados_clinicos
    r.dados_clinicos_organizados.localizacao=d.localizacao
    for origem,destino in [('comprimento','comprimento'),('largura','largura'),('tipoExsudato','tipo_exsudato'),('odor','odor'),('nivelDor','nivel_dor'),('queixaPrincipal','queixa_principal'),('observacoes','observacoes')]:
        valor=getattr(d,origem)
        setattr(r.dados_clinicos_organizados,destino,valor)
        if valor is None or valor=='':r.dados_clinicos_organizados.dados_nao_informados.append(destino)
    r.medidas.comprimento_informado_cm=d.comprimento
    r.medidas.largura_informada_cm=d.largura
    r.medidas.observacoes=['Comprimento e largura informados pelo profissional; área não calculada sem método validado.']
    return r
