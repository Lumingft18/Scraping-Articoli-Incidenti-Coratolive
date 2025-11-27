"""Calcolo di metriche descrittive sugli incidenti."""
from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict
from typing import Sequence

import pandas as pd


def build_metrics(records: Sequence[dict]) -> dict:
    df = pd.DataFrame(records)
    if df.empty:
        return {}

    df["date"] = pd.to_datetime(df["date"])
    per_year = df.groupby(df["date"].dt.year)["id"].count().to_dict()
    per_month = (
        df.groupby([df["date"].dt.to_period("M")])["id"].count().sort_index().tail(24)
    )
    per_month = {str(idx): int(val) for idx, val in per_month.items()}

    severity = df["severity"].value_counts().to_dict()
    roads = Counter(
        road.strip().title()
        for values in df["roads"].dropna()
        for road in values
        if isinstance(values, list)
    ).most_common(10)
    cities = Counter(
        city.strip().title()
        for values in df["cities"].dropna()
        for city in values
        if isinstance(values, list)
    ).most_common(10)

    return {
        "totale_articoli": int(len(df)),
        "periodo": {
            "min": df["date"].min().date().isoformat(),
            "max": df["date"].max().date().isoformat(),
        },
        "per_anno": {int(k): int(v) for k, v in per_year.items()},
        "per_mese": per_month,
        "per_severita": {k: int(v) for k, v in severity.items()},
        "top_strade": roads,
        "top_citta": cities,
    }


def save_metrics(metrics: dict, path: str | pathlib.Path) -> str:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)
    return str(path)
