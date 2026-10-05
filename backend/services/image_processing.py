import cv2
import numpy as np
import os


class ImageProcessingService:
    @staticmethod
    def processar_imagem_lesao(
        caminho_imagem_original: str,
        pasta_destino_processadas: str
    ) -> dict:
        """
        Realiza o processamento técnico inicial da imagem.

        Etapas:
        1. Validação da imagem.
        2. Extração das dimensões e quantidade de canais.
        3. Cálculo de brilho médio e contraste global.
        4. Redimensionamento proporcional, quando necessário.
        5. Salvamento da imagem pré-processada.

        Esta etapa não realiza diagnóstico, classificação ou
        interpretação clínica da lesão.
        """

        # ============================================================
        # 1. LEITURA E VALIDAÇÃO DA IMAGEM
        # ============================================================

        imagem_original = cv2.imread(
            caminho_imagem_original
        )

        if imagem_original is None:
            raise ValueError(
                "O arquivo enviado não pôde ser lido "
                "como uma imagem válida."
            )

        # ============================================================
        # 2. INFORMAÇÕES BÁSICAS DA IMAGEM
        # ============================================================

        altura, largura = imagem_original.shape[:2]

        if len(imagem_original.shape) == 2:
            canais = 1
        else:
            canais = imagem_original.shape[2]

        total_pixels = largura * altura

        # ============================================================
        # 3. ANÁLISE TÉCNICA BÁSICA
        # ============================================================

        # Conversão temporária para escala de cinza.
        # A imagem original permanece preservada.
        imagem_cinza = cv2.cvtColor(
            imagem_original,
            cv2.COLOR_BGR2GRAY
        )

        # Brilho médio da imagem.
        # Faixa aproximada: 0 a 255.
        brilho_medio = float(
            np.mean(imagem_cinza)
        )

        # Variação global das intensidades.
        # É apresentada apenas como uma métrica técnica
        # da imagem, sem interpretação clínica.
        contraste_global = float(
            np.std(imagem_cinza)
        )

        # ============================================================
        # 4. REDIMENSIONAMENTO PROPORCIONAL
        # ============================================================

        max_dimensao = 1280

        maior_dimensao = max(
            largura,
            altura
        )

        if maior_dimensao > max_dimensao:

            fator = (
                max_dimensao /
                maior_dimensao
            )

            nova_largura = max(
                1,
                int(largura * fator)
            )

            nova_altura = max(
                1,
                int(altura * fator)
            )

            imagem_processada = cv2.resize(
                imagem_original,
                (
                    nova_largura,
                    nova_altura
                ),
                interpolation=cv2.INTER_AREA
            )

            redimensionada = True

        else:

            imagem_processada = (
                imagem_original.copy()
            )

            nova_largura = largura
            nova_altura = altura

            redimensionada = False

        # ============================================================
        # 5. CRIAR DIRETÓRIO DE DESTINO
        # ============================================================

        os.makedirs(
            pasta_destino_processadas,
            exist_ok=True
        )

        # ============================================================
        # 6. SALVAR IMAGEM PROCESSADA
        # ============================================================

        nome_arquivo = os.path.basename(
            caminho_imagem_original
        )

        nome_processado = (
            f"proc_{nome_arquivo}"
        )

        caminho_saida = os.path.join(
            pasta_destino_processadas,
            nome_processado
        )

        sucesso_gravacao = cv2.imwrite(
            caminho_saida,
            imagem_processada
        )

        if not sucesso_gravacao:
            raise ValueError(
                "Não foi possível salvar "
                "a imagem pré-processada."
            )

        # ============================================================
        # 7. RETORNO ESTRUTURADO
        # ============================================================

        return {

            "dimensoes_originais": {

                "largura_pixels":
                    largura,

                "altura_pixels":
                    altura,

                "canais":
                    canais,

                "total_pixels":
                    total_pixels
            },

            "dimensoes_processadas": {

                "largura_pixels":
                    nova_largura,

                "altura_pixels":
                    nova_altura
            },

            "analise_tecnica": {

                "brilho_medio":
                    round(
                        brilho_medio,
                        2
                    ),

                "contraste_global":
                    round(
                        contraste_global,
                        2
                    )
            },

            "processamento_aplicado": {

                "validacao_imagem":
                    True,

                "conversao_temporaria_para_escala_de_cinza":
                    True,

                "redimensionamento_proporcional":
                    redimensionada,

                "dimensao_maxima":
                    max_dimensao
            },

            "nome_arquivo_processado":
                nome_processado
        }