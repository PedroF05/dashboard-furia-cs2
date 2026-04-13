# 🎮 FURIA Performance Dashboard – Power BI

Este projeto consiste em um dashboard interativo desenvolvido para análise de desempenho da equipe **FURIA Esports** no cenário competitivo de CS2, com foco em **visualização de dados, comparação de confrontos e identificação de tendências**.

O objetivo foi transformar dados públicos em **insights claros e acessíveis**, mesmo utilizando uma API com limitações na versão gratuita.

---

## 📊 Funcionalidades

* **Visão Geral** com indicadores principais (win rate, sequência atual e últimos resultados)
* **Análise temporal** do desempenho ao longo dos anos
* **Histórico de partidas** com informações de adversários, campeonatos e tiers
* **Próximos confrontos** para acompanhamento do cenário atual
* **Versus (Head-to-Head)** com análise detalhada contra adversários específicos
* **Desempenho por Tier e Formato** (MD3, MD5, etc.)

---

## 🧰 Tecnologias Utilizadas

* API PandaScore (coleta de dados)
* Python (ETL, automação e integração com API)
* SQLite (armazenamento local dos dados)
* Microsoft Power BI (modelagem de dados, DAX e criação do painel interativo)

---

## ⚠️ Observações

A versão gratuita da API PandaScore apresenta limitações quanto a dados detalhados de jogadores e estatísticas avançadas de partidas.

Mesmo assim, o projeto foi desenvolvido com foco em:
- extração de valor a partir de dados agregados  
- construção de análises relevantes com base em dados disponíveis  
- boas práticas de visualização e storytelling  

---

## 📂 Estrutura do Projeto
furia_cs2/
│
├── data/
│ └── recipients.csv
│
├── database/
│ ├── db.py
│ ├── furia_cs2.db
│ └── players_manual.sql
│
├── logs/
│
├── src/
│ ├── api_client.py
│ ├── email_notify.py
│ ├── fetch_matches.py
│ └── fetch_team.py
│
├── config.py
└── main.py


---

## 📎 Arquivos Principais

* `main.py`: Orquestração do pipeline de coleta e atualização dos dados  
* `api_client.py`: Integração com a API PandaScore  
* `fetch_matches.py`: Coleta de partidas  
* `fetch_team.py`: Coleta de informações do time  
* `db.py`: Manipulação do banco de dados SQLite  
* `furia_cs2.db`: Base consolidada utilizada no dashboard  
* `players_manual.sql`: Script complementar para dados de jogadores  

---

## 📎 Prints do Painel

### 🔹 Visão Geral

![Visão Geral](prints/visao_geral.png)

### 🔹 Versus

![Versus](prints/versus.png)

---

## 🎯 Objetivo

Aplicar conceitos de **Business Intelligence e Engenharia de Dados** em um contexto real do cenário de eSports, explorando diferentes formas de visualização e interpretação de performance competitiva.

---

Sinta-se à vontade para clonar, adaptar ou utilizar este projeto como referência de estudo e aprendizado.

📬 Para dúvidas, sugestões ou colaborações:  
https://www.linkedin.com/in/pedro-henrique-freitas-santos-b93200283/

---

#PowerBI #DataAnalytics #eSports #CS2 #FURIA #Dashboard #DataEngineering #BusinessIntelligence
