"""Utility per pulire il testo HTML e generare feature."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, List, Sequence

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from unidecode import unidecode

WHITESPACE_RE = re.compile(r"\s+")
ROAD_RE = re.compile(
    r"\b(?:sp\s?\d+|ss\s?\d+|ex\s?\d+|strada\s+provinciale\s+\d+|strada\s+statale\s+\d+|via\s+[A-ZÀ-Ù][^,.;]+|piazza\s+[A-ZÀ-Ù][^,.;]+)",
    re.IGNORECASE,
)
CITY_RE = re.compile(
    r"\b(?:Corato|Andria|Ruvo|Bisceglie|Trani|Bari|Bitonto|Altamura|Terlizzi|Giovinazzo|Molfetta|Barletta|Canosa)\b",
    re.IGNORECASE,
)
SEVERITY_MAP = {
    "morto": "fatale",
    "morta": "fatale",
    "decesso": "fatale",
    "codice rosso": "grave",
    "gravi": "grave",
    "grave": "grave",
    "feriti": "moderato",
    "ferito": "moderato",
}


def strip_html(value: str) -> str:
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text(" ")
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize(text: str) -> str:
    return unidecode(text or "").lower()


def extract_mentions(pattern: re.Pattern, text: str, limit: int = 5) -> List[str]:
    found = []
    for match in pattern.finditer(text):
        mention = WHITESPACE_RE.sub(" ", match.group().strip())
        if mention.lower() not in {m.lower() for m in found}:
            found.append(mention)
        if len(found) >= limit:
            break
    return found


def extract_date_parts(date_str: str) -> dict:
    dt = date_parser.parse(date_str)
    return {
        "date": dt.date().isoformat(),
        "datetime": dt.isoformat(),
        "year": dt.year,
        "month": dt.month,
        "month_name": dt.strftime("%B"),
        "weekday": dt.strftime("%A"),
    }


def guess_severity(text: str) -> str:
    ntext = normalize(text)
    ranking = ["fatale", "grave", "moderato"]
    severity = "informativo"
    for keyword, level in SEVERITY_MAP.items():
        if keyword in ntext:
            if ranking.index(level if level != "informativo" else "moderato") < ranking.index(severity if severity != "informativo" else "moderato"):
                severity = level
    return severity


def flag_keywords(text: str, keywords: Sequence[str]) -> List[str]:
    ntext = normalize(text)
    return [kw for kw in keywords if kw.lower() in ntext]


def detect_locations(text: str) -> dict:
    mentions = extract_mentions(ROAD_RE, text)
    cities = extract_mentions(CITY_RE, text)
    return {"roads": mentions, "cities": cities}
