"""Wrapper semplice per l'API REST di WordPress."""
from __future__ import annotations

import logging
import time
from typing import Dict, Iterable, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import USER_AGENT, WP_API_BASE

logger = logging.getLogger(__name__)


class WordPressClient:
    """Client minimale per leggere i post da WordPress."""

    def __init__(
        self,
        base_api: str = WP_API_BASE,
        *,
        throttle_seconds: float = 0.5,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_api = base_api.rstrip("/")
        self.throttle_seconds = throttle_seconds
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        retry = Retry(
            total=7,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_posts(
        self,
        *,
        search: Optional[str] = None,
        tags: Optional[List[int]] = None,
        categories: Optional[List[int]] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        per_page: int = 100,
        max_pages: Optional[int] = None,
        embed: bool = True,
    ) -> Iterable[Dict]:
        """Genera i post rispettando la paginazione dell'API."""

        page = 1
        total_yielded = 0
        while True:
            params = {
                "per_page": per_page,
                "page": page,
                "orderby": "date",
                "order": "desc",
            }
            if search:
                params["search"] = search
            if tags:
                params["tags"] = ",".join(str(tag) for tag in tags)
            if categories:
                params["categories"] = ",".join(str(cat) for cat in categories)
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            if embed:
                params["_embed"] = "1"

            url = f"{self.base_api}/posts"
            logger.debug("Richiesta pagina %d: %s params=%s", page, url, params)
            try:
                resp = self.session.get(url, params=params, timeout=90)
            except requests.RequestException as exc:
                logger.warning("Errore durante la richiesta a %s: %s", url, exc)
                break
            resp.raise_for_status()
            data: List[Dict] = resp.json()
            if not data:
                logger.debug("Pagina %d vuota, fine recupero", page)
                break
            for post in data:
                yield post
                total_yielded += 1

            if len(data) < per_page:
                logger.debug("Pagina %d con meno di %d risultati, fine recupero", page, per_page)
                break
            page += 1
            if max_pages and page > max_pages:
                logger.debug("Raggiunto limite di %d pagine", max_pages)
                break
            time.sleep(self.throttle_seconds)
        
        if page > 1:
            logger.info("Recuperate %d pagine, totale %d post", page - 1, total_yielded)
