"""
config.py — Configurações globais do projeto FURIA CS2 Dashboard
"""

import os

# ── PandaScore API ─────────────────────────────────────────────────────────────
API_KEY   = "COLOQUE SUA CHAVE"
BASE_URL  = "https://api.pandascore.co"
TEAM_SLUG = "furia"
TEAM_NAME = "FURIA"
PAGE_SIZE = 100

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, "database", "furia_cs2.db")
LOG_PATH      = os.path.join(BASE_DIR, "logs", "pipeline.log")
EXPORT_DIR    = os.path.join(BASE_DIR, "exports")
RECIPIENTS_CSV = os.path.join(BASE_DIR, "data", "recipients.csv")

# ── Gmail SMTP ─────────────────────────────────────────────────────────────────
# Preencha com sua conta Gmail e uma App Password
# (Google → Conta → Segurança → Senhas de app)
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "COLOQUE SEU E-MAIL"       # <- altere
SMTP_PASSWORD = "COLOQUE SUA CHAVE DE ACESSO"     # <- altere (App Password, não senha normal)
EMAIL_FROM    = "FURIA CS2 Dashboard <seu_email@gmail.com>"

# ── Lógica de notificação ──────────────────────────────────────────────────────
# Envia alerta a partir de N dias antes da partida
NOTIFY_DAYS_BEFORE = 7

# Quantas partidas recentes mostrar no resumo semanal
RECENT_MATCHES_COUNT = 5
