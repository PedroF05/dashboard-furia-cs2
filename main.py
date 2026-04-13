"""
main.py — Orquestrador do pipeline FURIA CS2 Dashboard
+ Aplica roster manual automaticamente após buscar o time ✅
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

from config import LOG_PATH, DB_PATH
from database.db import create_tables, migrate_all, get_connection

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger("main")


def apply_manual_roster() -> None:
    """
    Aplica o roster manual (players_manual.sql) após criar/atualizar o banco.
    Roda automaticamente quando --team é executado.
    """
    import sqlite3
    
    # Caminho para o SQL manual (na mesma pasta do db.py)
    sql_path = os.path.join(os.path.dirname(__file__), "database", "players_manual.sql")
    
    if not os.path.exists(sql_path):
        logger.warning("⚠️ players_manual.sql não encontrado. Pulando roster manual.")
        return
    
    try:
        logger.info("🔄 Aplicando roster manual...")
        
        with get_connection() as conn:
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            conn.executescript(sql_script)
        
        # Verifica quantos players foram salvos
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM players WHERE team_id=124530 AND active=1"
            )
            count = cursor.fetchone()[0]
        
        logger.info(f"✅ Roster manual aplicado: {count} jogadores ativos!")
        
    except FileNotFoundError:
        logger.warning("⚠️ players_manual.sql não encontrado. Pulando.")
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar roster manual: {e}")


def run_pipeline(args: argparse.Namespace) -> None:
    t0 = time.time()
    logger.info("=" * 60)
    logger.info(f"FURIA CS2 Pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info("=" * 60)

    create_tables()
    migrate_all()

    run_all = not any([args.team, args.matches, args.export, args.email])
    team_id: int = 0

    # ── 1. Time + Jogadores ───────────────────────────────────────────────────
    if run_all or args.team:
        logger.info("── ETAPA 1: Time e Jogadores ──")
        from src.fetch_team import run as run_team
        team = run_team()
        if not team:
            logger.error("Time não encontrado. Abortando.")
            sys.exit(1)
        team_id = team["id"]
        
        # ✅ APLICA ROSTER MANUAL AUTOMATICAMENTE
        apply_manual_roster()

    if not team_id:
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM team LIMIT 1").fetchone()
            if row:
                team_id = row[0]

    if not team_id and (run_all or args.matches):
        logger.error("team_id não encontrado. Rode: python main.py --team")
        sys.exit(1)

    # ── 2. Partidas ───────────────────────────────────────────────────────────
    if run_all or args.matches:
        logger.info("── ETAPA 2: Partidas ──")
        logger.info("  • Finalizadas: ✅")
        logger.info("  • Futuras: ✅")
        logger.info("  • Logos: 🎨")
        logger.info("  • Troféus: 🏆")
        
        from src.fetch_matches import run as run_matches
        run_matches(team_id)

    # ── 3. Email ──────────────────────────────────────────────────────────────
    if run_all or args.email:
        logger.info("── ETAPA 3: Notificação por Email ──")
        from src.email_notify import run as run_email
        run_email(force=args.force)

    logger.info(f"Pipeline concluído em {time.time() - t0:.1f}s")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline FURIA CS2 → SQLite → Power BI + Email")
    parser.add_argument("--team",    action="store_true", help="Busca time e jogadores")
    parser.add_argument("--matches", action="store_true", help="Busca partidas")
    parser.add_argument("--export",  action="store_true", help="Exporta CSVs")
    parser.add_argument("--email",   action="store_true", help="Envia email")
    parser.add_argument("--force",   action="store_true", help="Força envio de email")
    
    args = parser.parse_args()
    
    if not any([args.team, args.matches, args.export, args.email]):
        args.team = args.matches = args.email = True
    
    run_pipeline(args)


if __name__ == "__main__":
    main()