-- ========================================
-- database/players_manual.sql
-- ROSTER MANUAL DA FURIA CS2 - VERSÃO LIMPA
-- Script para rodar: 
-- ========================================

-- Desativa players antigos (mantém histórico)
UPDATE players SET active = 0 WHERE team_id = 124530;

-- Insere roster atual (SEM comentários inline!)
INSERT OR REPLACE INTO players (
    id, team_id, name, first_name, last_name, 
    nationality, age, role, image_url, active, updated_at
) VALUES 
(100001, 124530, 'FalleN', 'Gabriel', 'Toledo', 'BR', 34, 'IGL', 'https://img-cdn.hltv.org/playerbodyshot/gQbb4I0TeHmxx7bYBOtd7T.png?ixlib=java-2.1.0&w=400&s=744dd676bd5ad23e4adfc8dc8fcbaa80', 1, datetime('now')),
(100002, 124530, 'KSCERATO', 'Kaike', 'Ceratoo', 'BR', 26, 'Entry Fragger', 'https://img-cdn.hltv.org/playerbodyshot/z0vT0V815B0MdeeKhcf44Y.png?ixlib=java-2.1.0&w=400&s=32afd770ba5023b0eefc0712e029065a', 1, datetime('now')),
(100003, 124530, 'molodoy', 'Danil', 'Golubenko', 'KZ', 21, 'AWP', 'https://img-cdn.hltv.org/playerbodyshot/oPoWLYFq87cIs2cYDo8id7.png?ixlib=java-2.1.0&w=400&s=26d135bacbf9f98ff775421c3ca2bf4c', 1, datetime('now')),
(100004, 124530, 'YEKINDAR', 'Mareks', 'Gaļinskis', 'LV', 26, 'Entry Fragger', 'https://img-cdn.hltv.org/playerbodyshot/IO3vEa2fT2qFPRlrPid7hf.png?ixlib=java-2.1.0&w=400&s=2826592c7787a70711b1ca5651ab25a7', 1, datetime('now')),
(100005, 124530, 'yuurih', 'Yuri', 'Santos', 'BR', 26, 'Lurker', 'https://img-cdn.hltv.org/playerbodyshot/ZapU9KMKIlH1bDpSlV6MO1.png?ixlib=java-2.1.0&w=400&s=09cb203041b92340db49939164bc6f99', 1, datetime('now')),
(100006, 124530, 'sidde', 'Sid', 'Macedo', 'BR', 29, 'Coach', 'https://img-cdn.hltv.org/playerbodyshot/tC0c78cxXd6470GcmDYM_5.png?ixlib=java-2.1.0&w=400&s=55a2a493d40b458f6d6e3d375e9fef66', 1, datetime('now'));