"""
src/fetch_matches.py — Busca TODAS as partidas da FURIA CS2
+ Extração de logos dos adversários para página Versus 🎨
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.api_client import get_all
from database.db import get_connection

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(d: Any, *keys, default=None) -> Any:
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def _resolve_opponent(match: Dict, furia_id: int) -> Dict:
    for entry in match.get("opponents", []) or []:
        opp = entry.get("opponent") or entry
        if isinstance(opp, dict) and opp.get("id") != furia_id:
            return opp
    return {}


def _resolve_score(match: Dict, furia_id: int) -> Tuple[Optional[int], Optional[int]]:
    furia_score = opp_score = None
    for r in match.get("results", []) or []:
        if r.get("team_id") == furia_id:
            furia_score = r.get("score")
        else:
            opp_score = r.get("score")
    return furia_score, opp_score


def _resolve_winner(match: Dict) -> Optional[str]:
    w = match.get("winner")
    if isinstance(w, dict):
        return w.get("name")
    return w if isinstance(w, str) else None


def _furia_in_match(match: Dict, furia_id: int) -> bool:
    for entry in match.get("opponents", []) or []:
        opp = entry.get("opponent") or entry
        if isinstance(opp, dict) and opp.get("id") == furia_id:
            return True
    return False


def _is_tournament_win(match: Dict, furia_id: int) -> bool:
    """
    Detecta troféus de forma SIMPLES e DIRETA:
    ✅ "Grand final" ou "Final" no nome da partida + FURIA venceu = 🏆 TROFÉU
    """
    # 1. FURIA precisa ter vencido a partida
    winner = match.get("winner")
    if not winner:
        return False
    
    winner_id = winner.get("id") if isinstance(winner, dict) else None
    if winner_id != furia_id:
        return False
    
    # 2. Extrai TODOS os campos possíveis onde pode ter "grand final"
    match_name = str(match.get("name", "")).lower()          
    match_type = str(match.get("match_type", "")).lower()
    tournament = match.get("tournament") or {}
    tournament_name = str(tournament.get("name", "")).lower()
    serie_name = str((match.get("serie") or {}).get("full_name", "")).lower()
    
    # 3. Combina tudo em uma string só para busca (case-insensitive)
    all_names = f"{match_name} {match_type} {tournament_name} {serie_name}"
    
    # 4. CRITÉRIO: "grand final" ou "final" no nome + FURIA venceu
    # (ajuste conforme precisar: só "grand final" ou incluir "final" também)
    if "grand final" in all_names:
        trophy_name = match.get("name") or tournament.get("name") or (match.get("serie") or {}).get("full_name")
        logger.info(f"🏆 TROFÉU (Grand Final): {trophy_name} | {match.get('begin_at')}")
        return True
    
    return False


def _extract_opponent_images(match: Dict, furia_id: int) -> Tuple[Optional[str], Optional[str]]:
    image_url = None
    dark_image_url = None
    
    for entry in match.get("opponents", []) or []:
        opp = entry.get("opponent") or entry
        if isinstance(opp, dict) and opp.get("id") != furia_id:
            image_url = opp.get("image_url")
            dark_image_url = opp.get("dark_mode_image_url")
            break
    
    return image_url, dark_image_url


def _build_row(m: Dict, furia_id: int) -> Dict:
    opp = _resolve_opponent(m, furia_id)
    furia_score, opp_score = _resolve_score(m, furia_id)
    tournament_won = _is_tournament_win(m, furia_id)
    tournament = m.get("tournament") or {}
    opp_image_url, opp_dark_image = _extract_opponent_images(m, furia_id)
    
    return {
        "id": m["id"],
        "name": m.get("name"),
        "status": m.get("status"),
        "match_type": m.get("match_type"),
        "scheduled_at": m.get("scheduled_at"),
        "begin_at": m.get("begin_at"),
        "end_at": m.get("end_at"),
        "opponent_id": opp.get("id"),
        "opponent_name": opp.get("name"),
        "opponent_acronym": opp.get("acronym"),
        "opponent_image_url": opp_image_url,
        "opponent_dark_image_url": opp_dark_image,
        "furia_score": furia_score,
        "opponent_score": opp_score,
        "winner": _resolve_winner(m),
        "draw": 1 if m.get("draw") else 0,
        "league_id": _safe(m, "league", "id"),
        "league_name": _safe(m, "league", "name"),
        "league_slug": _safe(m, "league", "slug"),
        "serie_id": _safe(m, "serie", "id"),
        "serie_name": _safe(m, "serie", "full_name") or _safe(m, "serie", "name"),
        "tournament_id": _safe(m, "tournament", "id"),
        "tournament_name": _safe(m, "tournament", "name"),
        "tournament_tier": _safe(m, "tournament", "tier"),
        "tournament_win": 1 if tournament_won else 0,
        "trophy_name": tournament.get("name") if tournament_won else None,
    }


UPSERT_SQL = """
    INSERT INTO matches (
        id, name, status, match_type, scheduled_at, begin_at, end_at,
        opponent_id, opponent_name, opponent_acronym,
        opponent_image_url, opponent_dark_image_url,
        furia_score, opponent_score, winner, draw,
        league_id, league_name, league_slug,
        serie_id, serie_name,
        tournament_id, tournament_name, tournament_tier,
        tournament_win, trophy_name
    ) VALUES (
        :id, :name, :status, :match_type, :scheduled_at, :begin_at, :end_at,
        :opponent_id, :opponent_name, :opponent_acronym,
        :opponent_image_url, :opponent_dark_image_url,
        :furia_score, :opponent_score, :winner, :draw,
        :league_id, :league_name, :league_slug,
        :serie_id, :serie_name,
        :tournament_id, :tournament_name, :tournament_tier,
        :tournament_win, :trophy_name
    )
    ON CONFLICT(id) DO UPDATE SET
        status = excluded.status,
        begin_at = excluded.begin_at,
        end_at = excluded.end_at,
        opponent_name = excluded.opponent_name,
        opponent_acronym = excluded.opponent_acronym,
        opponent_image_url = excluded.opponent_image_url,
        opponent_dark_image_url = excluded.opponent_dark_image_url,
        furia_score = excluded.furia_score,
        opponent_score = excluded.opponent_score,
        winner = excluded.winner,
        draw = excluded.draw,
        tournament_name = excluded.tournament_name,
        tournament_tier = excluded.tournament_tier,
        serie_name = excluded.serie_name,
        league_name = excluded.league_name,
        tournament_win = excluded.tournament_win,
        trophy_name = excluded.trophy_name
"""


def _fetch_team_matches(team_id: int, status: str, sort: str, per_page: int = 100) -> List[Dict]:
    endpoint = f"/teams/{team_id}/matches"
    params = {
        "filter[status]": status if status else "all",
        "sort": sort,
        "per_page": per_page
    }
    
    try:
        logger.debug(f"GET {endpoint} params={params}")
        all_matches = get_all(endpoint, params)
        logger.info(f"  📥 API retornou {len(all_matches)} partidas totais (status='{status}')")
        
        if not all_matches:
            return []
        
        filtered = [m for m in all_matches if _furia_in_match(m, team_id)]
        logger.info(f"  ✅ Após filtro FURIA: {len(filtered)} partidas válidas")
        return filtered
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar partidas (status={status}): {e}")
        return []


def fetch_past_matches(team_id: int) -> List[Dict]:
    logger.info("Buscando partidas finalizadas...")
    matches = _fetch_team_matches(team_id, status="finished", sort="-begin_at", per_page=100)
    rows = [_build_row(m, team_id) for m in matches]
    with get_connection() as conn:
        conn.executemany(UPSERT_SQL, rows)
    logger.info(f"  ✓ {len(rows)} partidas finalizadas salvas.")
    return rows


def fetch_upcoming_matches(team_id: int) -> List[Dict]:
    logger.info("Buscando partidas futuras...")
    matches = _fetch_team_matches(team_id, status="not_started", sort="scheduled_at", per_page=50)
    rows = [_build_row(m, team_id) for m in matches]
    with get_connection() as conn:
        conn.executemany(UPSERT_SQL, rows)
    logger.info(f"  ✓ {len(rows)} partidas futuras salvas.")
    return rows


def run(team_id: int) -> None:
    fetch_past_matches(team_id)
    fetch_upcoming_matches(team_id)