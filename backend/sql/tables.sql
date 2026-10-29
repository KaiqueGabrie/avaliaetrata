
-- ============================================================
-- AVALIA & TRATA
-- BANCO DE DADOS MYSQL - DER REVISADO
-- ============================================================

CREATE DATABASE IF NOT EXISTS avalia_trata
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE avalia_trata;

-- ============================================================
-- 1. INSTITUICAO DE SAUDE
-- ============================================================

CREATE TABLE IF NOT EXISTS instituicao_saude (
    id_instituicao INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    cnpj VARCHAR(14) UNIQUE,
    telefone VARCHAR(20),
    email VARCHAR(150),
    endereco VARCHAR(255),

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL
) ENGINE=InnoDB;

-- ============================================================
-- 2. ENFERMEIRO
-- ============================================================

CREATE TABLE IF NOT EXISTS enfermeiro (
    id_enfermeiro INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) NOT NULL UNIQUE,
    data_nascimento DATE,
    telefone VARCHAR(20),
    registro_coren VARCHAR(30),

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL
) ENGINE=InnoDB;

-- A coluna senha deverá armazenar apenas hash seguro,
-- nunca a senha original do profissional.

-- ============================================================
-- 3. VINCULO ENFERMEIRO / INSTITUICAO
-- ============================================================

CREATE TABLE IF NOT EXISTS enfermeiro_instituicao (
    id_vinculo INT AUTO_INCREMENT PRIMARY KEY,
    id_enfermeiro_fk INT NOT NULL,
    id_instituicao_fk INT NOT NULL,
    data_inicio DATE,
    data_fim DATE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_vinculo_enfermeiro
        FOREIGN KEY (id_enfermeiro_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    CONSTRAINT fk_vinculo_instituicao
        FOREIGN KEY (id_instituicao_fk)
        REFERENCES instituicao_saude(id_instituicao),

    INDEX idx_vinculo_enfermeiro (id_enfermeiro_fk),
    INDEX idx_vinculo_instituicao (id_instituicao_fk)
) ENGINE=InnoDB;

-- ============================================================
-- 4. PACIENTE
-- ============================================================

CREATE TABLE IF NOT EXISTS paciente (
    id_paciente INT AUTO_INCREMENT PRIMARY KEY,
    id_enfermeiro_fk INT NOT NULL,
    id_instituicao_fk INT NULL,

    nome_completo VARCHAR(150) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    telefone VARCHAR(20),
    email VARCHAR(150) UNIQUE,
    diagnostico VARCHAR(200),
    local_lesao VARCHAR(100),
    status_evolucao VARCHAR(10),
    data_cadastro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    CONSTRAINT fk_paciente_enfermeiro
        FOREIGN KEY (id_enfermeiro_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    CONSTRAINT fk_paciente_instituicao
        FOREIGN KEY (id_instituicao_fk)
        REFERENCES instituicao_saude(id_instituicao),

    INDEX idx_paciente_enfermeiro (id_enfermeiro_fk),
    INDEX idx_paciente_instituicao (id_instituicao_fk)
) ENGINE=InnoDB;

-- ============================================================
-- 5. ANAMNESE
-- Uma anamnese por paciente.
-- Atualizavel no perfil, sem recriar a cada consulta.
-- ============================================================

CREATE TABLE IF NOT EXISTS anamnese (
    id_anamnese INT AUTO_INCREMENT PRIMARY KEY,
    id_paciente_fk INT NOT NULL UNIQUE,

    historia_pregressa TEXT,
    tabagismo TINYINT,
    mobilidade_reduzida TINYINT,
    possui_varizes TINYINT,
    historico_amputacao TINYINT,
    pulsos_perifericos VARCHAR(20),
    data_surgimento_ferida DATE,
    causa_provavel VARCHAR(50),
    outras_patologias TEXT,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    CONSTRAINT fk_anamnese_paciente
        FOREIGN KEY (id_paciente_fk)
        REFERENCES paciente(id_paciente)
) ENGINE=InnoDB;

-- ============================================================
-- 6. ANALISE
-- Cada consulta gera uma nova analise.
-- ============================================================

CREATE TABLE IF NOT EXISTS analise (
    id_analise INT AUTO_INCREMENT PRIMARY KEY,
    id_paciente_fk INT NOT NULL,
    id_enfermeiro_fk INT NOT NULL,

    data_analise DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    queixa_principal TEXT,
    observacoes_clinicas TEXT,
    relatorio_texto TEXT,

    area_estimada DECIMAL(6,2),
    tecido_granulacao DECIMAL(5,2),
    tecido_esfacelo DECIMAL(5,2),
    tecido_necrose DECIMAL(5,2),

    status VARCHAR(20) NOT NULL DEFAULT 'pendente',

    -- Copia do contexto clinico usado pelas IAs.
    -- Nao muda quando a anamnese e atualizada.
    contexto_clinico_json JSON,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    CONSTRAINT fk_analise_paciente
        FOREIGN KEY (id_paciente_fk)
        REFERENCES paciente(id_paciente),

    CONSTRAINT fk_analise_enfermeiro
        FOREIGN KEY (id_enfermeiro_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    INDEX idx_analise_paciente (id_paciente_fk),
    INDEX idx_analise_enfermeiro (id_enfermeiro_fk),
    INDEX idx_analise_data (data_analise)
) ENGINE=InnoDB;

-- ============================================================
-- 7. IMAGEM
-- Mantem o relacionamento 1:1 do DER original.
-- ============================================================

CREATE TABLE IF NOT EXISTS imagem (
    id_imagem INT AUTO_INCREMENT PRIMARY KEY,
    id_analise_fk INT NOT NULL UNIQUE,

    caminho_imagem_original VARCHAR(255),
    caminho_imagem_marcada VARCHAR(255),
    data_captura DATETIME,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    CONSTRAINT fk_imagem_analise
        FOREIGN KEY (id_analise_fk)
        REFERENCES analise(id_analise)
) ENGINE=InnoDB;

-- ============================================================
-- 8. RELATORIO DE IA
-- Cada IA possui um relatorio independente.
-- ============================================================

CREATE TABLE IF NOT EXISTS relatorio_ia (
    id_relatorio CHAR(36) PRIMARY KEY,
    id_analise_fk INT NOT NULL,

    provedor VARCHAR(20) NOT NULL,
    conteudo_original JSON NOT NULL,
    conteudo_editavel JSON NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'gerado',
    alertas_validacao JSON,
    revisao_profissional_necessaria BOOLEAN
        NOT NULL DEFAULT TRUE,

    data_processamento DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    profissional_responsavel_fk INT NULL,
    data_aprovacao DATETIME NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_relatorio_analise
        FOREIGN KEY (id_analise_fk)
        REFERENCES analise(id_analise),

    CONSTRAINT fk_relatorio_profissional
        FOREIGN KEY (profissional_responsavel_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    CONSTRAINT uq_relatorio_analise_provedor
        UNIQUE (id_analise_fk, provedor),

    CONSTRAINT chk_relatorio_provedor
        CHECK (provedor IN ('openai', 'gemini', 'kimi')),

    CONSTRAINT chk_relatorio_status
        CHECK (status IN ('gerado', 'em_edicao', 'aprovado')),

    INDEX idx_relatorio_analise (id_analise_fk)
) ENGINE=InnoDB;

-- ============================================================
-- 9. HISTORICO DE EDICAO
-- Registra cada alteracao feita pelo enfermeiro.
-- ============================================================

CREATE TABLE IF NOT EXISTS historico_edicao (
    id_edicao BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_relatorio_fk CHAR(36) NOT NULL,
    id_enfermeiro_fk INT NOT NULL,

    campo VARCHAR(150) NOT NULL,
    valor_anterior JSON,
    valor_novo JSON,

    data_edicao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_edicao_relatorio
        FOREIGN KEY (id_relatorio_fk)
        REFERENCES relatorio_ia(id_relatorio),

    CONSTRAINT fk_edicao_enfermeiro
        FOREIGN KEY (id_enfermeiro_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    INDEX idx_edicao_relatorio (id_relatorio_fk)
) ENGINE=InnoDB;

-- ============================================================
-- 10. LOG DE AUDITORIA
-- ============================================================

CREATE TABLE IF NOT EXISTS log_auditoria (
    id_log BIGINT AUTO_INCREMENT PRIMARY KEY,

    id_enfermeiro_fk INT NULL,
    acao VARCHAR(100) NOT NULL,
    entidade VARCHAR(100) NOT NULL,
    registro_id VARCHAR(50),

    id_analise_fk INT NULL,
    detalhes JSON,

    data_evento DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_log_enfermeiro
        FOREIGN KEY (id_enfermeiro_fk)
        REFERENCES enfermeiro(id_enfermeiro),

    CONSTRAINT fk_log_analise
        FOREIGN KEY (id_analise_fk)
        REFERENCES analise(id_analise),

    INDEX idx_log_data (data_evento),
    INDEX idx_log_entidade (entidade, registro_id)
) ENGINE=InnoDB;

-- ============================================================
-- VERIFICACAO FINAL
-- ============================================================

SHOW TABLES;

SELECT
    COUNT(*) AS quantidade_tabelas
FROM information_schema.tables
WHERE table_schema = 'avalia_trata'
  AND table_type = 'BASE TABLE';
