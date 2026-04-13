"""
src/fetch_team.py — Busca dados do time FURIA da API
Players são gerenciados manualmente via database/players_manual.sql
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.api_client import get_all
from database.db import get_connection
from config import TEAM_SLUG

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(d: Any, *keys, default=None) -> Any:
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def fetch_team() -> Optional[Dict]:
    """Busca dados do time FURIA da API e salva no banco"""
    logger.info("Buscando time FURIA...")
    teams = get_all("/csgo/teams", {"filter[slug]": TEAM_SLUG})
    
    if not teams:
        logger.error(f"Time '{TEAM_SLUG}' não encontrado.")
        return None

    t = teams[0]
    row = {
        "id": t["id"],
        "name": t.get("name"),
        "slug": t.get("slug"),
        "acronym": t.get("acronym"),
        "location": t.get("location"),
        "image_url": t.get("image_url"),
        "updated_at": _now(),
    }
    
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO team
              (id, name, slug, acronym, location, image_url, updated_at)
            VALUES
              (:id, :name, :slug, :acronym, :location, :image_url, :updated_at)
        """, row)
    
    logger.info(f"Time salvo: {row['name']} (id={row['id']})")
    return t


def fetch_players_manual_hint() -> None:
    """
    Mensagem informativa: players são gerenciados manualmente.
    
    Para atualizar o roster:
    1. Edite database/players_manual.sql
    2. Rode: sqlite3 database/furia.db < database/players_manual.sql
    """
    logger.info("⚠️ Players gerenciados manualmente")
    logger.info("   Para atualizar: edite database/players_manual.sql e rode o script SQL")


def run() -> Optional[Dict]:
    """
    Executa a coleta do time FURIA.
    
    ✅ Time: busca da API (automático)
    ⚠️ Players: gerenciados manualmente (ver database/players_manual.sql)
    """
    team = fetch_team()
    
    if team:
        # ❌ fetch_players(team["id"])  ← REMOVIDO: players agora são manuais
        fetch_players_manual_hint()
    
    return team