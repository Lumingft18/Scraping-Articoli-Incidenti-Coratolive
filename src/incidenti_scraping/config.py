"""Configurazioni condivise per lo scraping di coratolive.it."""
from __future__ import annotations

BASE_URL = "https://coratolive.it"
WP_API_BASE = f"{BASE_URL}/wp-json/wp/v2"
USER_AGENT = "IncidentiScraper/0.1 (+https://github.com/)"
DEFAULT_KEYWORDS = [
    "incidente",
    "sinistro",
    "tamponamento",
    "investimento",
    "scontro",
    "travolto",
    "schianto",
    "ribaltamento",
    "feriti",
    "morto",
]
# tag_id 242 corrisponde a "incidente" (verificato dagli endpoint WP)
INCIDENT_TAG_ID = 242
