"""
src/api_client.py — Cliente HTTP PandaScore com paginação e rate-limit automático
"""

import time
import logging
import requests
from typing import Any, Dict, Iterator, List, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import API_KEY, BASE_URL, PAGE_SIZE

logger = logging.getLogger(__name__)

_MIN_INTERVAL = 1.1   # free tier ~1 req/s
_last_call: float = 0.0


def _throttle() -> None:
    global _last_call
    wait = _MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def get(endpoint: str, params: Optional[Dict] = None) -> Any:
    _throttle()
    params = dict(params or {})
    params["token"] = API_KEY
    url = f"{BASE_URL}{endpoint}"

    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code == 429:
        logger.warning("Rate limit — aguardando 60s...")
        time.sleep(60)
        return get(endpoint, params)

    resp.raise_for_status()
    return resp.json()


def paginate(endpoint: str, params: Optional[Dict] = None) -> Iterator[List[Any]]:
    params = dict(params or {})
    params["per_page"] = PAGE_SIZE
    page = 1
    while True:
        params["page"] = page
        data = get(endpoint, params)
        if not data:
            break
        yield data
        if len(data) < PAGE_SIZE:
            break
        page += 1


def get_all(endpoint: str, params: Optional[Dict] = None) -> List[Any]:
    result = []
    for page in paginate(endpoint, params):
        result.extend(page)
    return result
