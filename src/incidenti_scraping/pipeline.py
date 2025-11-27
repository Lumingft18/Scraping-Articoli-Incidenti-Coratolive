"""Pipeline per raccogliere, filtrare e trasformare i post di coratolive.it."""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Dict, Iterable, List, Sequence

import pandas as pd

from .config import DEFAULT_KEYWORDS, INCIDENT_TAG_ID
from .text_utils import (
    detect_locations,
    extract_date_parts,
    flag_keywords,
    guess_severity,
    normalize,
    strip_html,
)
from .wordpress_client import WordPressClient

logger = logging.getLogger(__name__)


def _pull_posts(keywords: Sequence[str], max_pages: int | None) -> Dict[int, Dict]:
    client = WordPressClient()
    posts: Dict[int, Dict] = {}

    def _add(post: Dict) -> None:
        posts[post["id"]] = post

    logger.info("Recupero articoli con tag incidente (max_pages=%s)", max_pages or "illimitato")
    count_before = len(posts)
    for post in client.fetch_posts(tags=[INCIDENT_TAG_ID], max_pages=max_pages):
        _add(post)
    logger.info("  → Recuperati %d nuovi post con tag incidente", len(posts) - count_before)

    for kw in keywords:
        logger.info("Recupero articoli con keyword '%s' (max_pages=%s)", kw, max_pages or "illimitato")
        count_before = len(posts)
        for post in client.fetch_posts(search=kw, max_pages=max_pages):
            full_text = normalize(strip_html(post["title"]["rendered"]) + " " + strip_html(post["content"]["rendered"]))
            if "inciden" in full_text or kw in full_text:
                _add(post)
        logger.info("  → Recuperati %d nuovi post con keyword '%s'", len(posts) - count_before, kw)

    return posts


def _post_to_record(post: Dict, keywords: Sequence[str]) -> Dict:
    title = strip_html(post["title"]["rendered"])
    excerpt = strip_html(post.get("excerpt", {}).get("rendered", ""))
    content = strip_html(post.get("content", {}).get("rendered", ""))
    full_text = f"{title}. {excerpt}. {content}".strip()
    matches = flag_keywords(full_text, keywords)
    severity = guess_severity(full_text)
    locations = detect_locations(full_text)
    date_parts = extract_date_parts(post["date"])

    embed = post.get("_embedded", {})
    categories = [cat.get("name") for cat in embed.get("wp:term", [[{}]])[0] if cat.get("taxonomy") == "category"] if embed else []
    tags = [tag.get("name") for tag in embed.get("wp:term", [[{}]])[1] if tag.get("taxonomy") == "post_tag"] if embed and len(embed.get("wp:term", [])) > 1 else []

    return {
        "id": post["id"],
        **date_parts,
        "title": title,
        "link": post.get("link"),
        "excerpt": excerpt,
        "content": content,
        "categories": categories,
        "tags": tags,
        "severity": severity,
        "keywords": matches,
        "roads": locations["roads"],
        "cities": locations["cities"],
    }


def collect_incidents(
    *,
    keywords: Sequence[str] | None = None,
    max_pages: int | None = None,
    limit: int | None = None,
) -> List[Dict]:
    keywords = keywords or DEFAULT_KEYWORDS
    posts = _pull_posts(keywords, max_pages)
    logger.info("Totale post recuperati: %s", len(posts))
    records = [_post_to_record(post, keywords) for post in posts.values()]
    records.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    if limit:
        records = records[:limit]
    return records


def save_dataset(records: Sequence[Dict], output_dir: str | pathlib.Path) -> dict:
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "incidents.json"
    parquet_path = output_dir / "incidents.parquet"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)

    df = pd.DataFrame(records)
    df.to_parquet(parquet_path, index=False)

    return {"json": str(json_path), "parquet": str(parquet_path), "count": len(records)}
