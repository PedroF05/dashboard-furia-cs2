"""
database/db.py — Schema SQLite e gerenciador de conexão
Tabelas: team · players · matches
+ Suporte a logos de times para página Versus 🎨
"""

import os
import sqlite3
import logging
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables() -> None:
    ddl = """
    -- ── Time (FURIA e adversários) ──────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS team (
        id                    INTEGER PRIMARY KEY,
        name                  TEXT,
        slug                  TEXT UNIQUE,
        acronym               TEXT,
        location              TEXT,
        image_url             TEXT,
        dark_mode_image_url   TEXT,
        modified_at           TEXT,
        updated_at            TEXT
    );

    -- ── Jogadores (roster atual) ───────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS players (
        id          INTEGER PRIMARY KEY,
        team_id     INTEGER REFERENCES team(id),
        name        TEXT,
        first_name  TEXT,
        last_name   TEXT,
        nationality TEXT,
        age         INTEGER,
        role        TEXT,
        image_url   TEXT,
        active      INTEGER DEFAULT 1,
        updated_at  TEXT
    );

    -- ── Partidas (passadas + futuras) ──────────────────────────────────────
    CREATE TABLE IF NOT EXISTS matches (
        id                      INTEGER PRIMARY KEY,
        name                    TEXT,
        status                  TEXT,
        match_type              TEXT,
        scheduled_at            TEXT,
        begin_at                TEXT,
        end_at                  TEXT,
        opponent_id             INTEGER,
        opponent_name           TEXT,
        opponent_acronym        TEXT,
        opponent_image_url      TEXT,
        opponent_dark_image_url TEXT,
        furia_score             INTEGER,
        opponent_score          INTEGER,
        winner                  TEXT,
        draw                    INTEGER DEFAULT 0,
        league_id               INTEGER,
        league_name             TEXT,
        league_slug             TEXT,
        serie_id                INTEGER,
        serie_name              TEXT,
        tournament_id           INTEGER,
        tournament_name         TEXT,
        tournament_tier         TEXT,
        tournament_win          INTEGER DEFAULT 0,
        trophy_name             TEXT,
        notified_days           TEXT DEFAULT '[]'
    );

    -- Índices para performance
    CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
    CREATE INDEX IF NOT EXISTS idx_matches_sched ON matches(scheduled_at);
    CREATE INDEX IF NOT EXISTS idx_matches_opponent ON matches(opponent_id);
    CREATE INDEX IF NOT EXISTS idx_matches_trophy ON matches(tournament_win) WHERE tournament_win = 1;
    """
    
    with get_connection() as conn:
        conn.executescript(ddl)
    logger.info("Schema verificado.")


def migrate_all() -> None:
    """Executa migrações para adicionar colunas de imagens dos adversários"""
    with get_connection() as conn:
        # === Migração: tabela matches ===
        cursor = conn.execute("PRAGMA table_info(matches)")
        matches_cols = [row["name"] for row in cursor.fetchall()]
        
        for col in ["opponent_image_url", "opponent_dark_image_url"]:
            if col not in matches_cols:
                logger.info(f"🔄 Migrando matches: adicionando {col}...")
                conn.execute(f"ALTER TABLE matches ADD COLUMN {col} TEXT")
        
        # === Migração: tabela team ===
        cursor = conn.execute("PRAGMA table_info(team)")
        team_cols = [row["name"] for row in cursor.fetchall()]
        
        for col in ["dark_mode_image_url", "modified_at"]:
            if col not in team_cols:
                logger.info(f"🔄 Migrando team: adicionando {col}...")
                conn.execute(f"ALTER TABLE team ADD COLUMN {col} TEXT")
        
        # === Criar índices ===
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_opponent ON matches(opponent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_trophy ON matches(tournament_win) WHERE tournament_win = 1")
        
        conn.commit()
    
    logger.info("✅ Migrações concluídas.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_tables()
    migrate_all()
    print(f"✅ Banco criado/atualizado em: {DB_PATH}")
    
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM matches")
        print(f"📊 Partidas no banco: {cursor.fetchone()[0]}")
        
        cursor = conn.execute("SELECT COUNT(*) FROM team")
        print(f"👥 Times no banco: {cursor.fetchone()[0]}")