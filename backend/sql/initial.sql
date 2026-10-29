
-- =====================================================
-- AVALIA & TRATA
-- =====================================================

-- 1. Criar o banco de dados
CREATE DATABASE IF NOT EXISTS avalia_trata
CHARACTER SET utf8mb4	
COLLATE utf8mb4_unicode_ci;

-- 2. Selecionar o banco
USE avalia_trata;


-- 4. Conceder permissões ao usuário
GRANT SELECT, INSERT, UPDATE, DELETE
ON avalia_trata.*
TO 'avalia_app'@'localhost';

-- 5. Verificar as permissões
SHOW GRANTS FOR 'avalia_app'@'localhost';

-- 6. Verificar o banco selecionado
SELECT DATABASE() AS banco_atual;

-- 7. Verificar a versão do MySQL
SELECT VERSION() AS versao_mysql;

-- 8. Confirmar que o banco existe
SHOW DATABASES LIKE 'avalia_trata';



