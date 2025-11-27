"""Esegue l'intera pipeline: scraping + metriche + export per dashboard."""
from __future__ import annotations

import argparse
import json
import logging
import pathlib

import sys

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
SRC_DIR = ROOT_DIR / "src"

for path in (SRC_DIR, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from incidenti_scraping.pipeline import collect_incidents, save_dataset
from analysis.metrics import build_metrics, save_metrics

# Importa la funzione di pulizia
CLEAN_SCRIPT = CURRENT_DIR / "clean_dataset.py"
if CLEAN_SCRIPT.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("clean_dataset", CLEAN_SCRIPT)
    clean_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clean_module)
    clean_dataset = clean_module.clean_dataset
else:
    clean_dataset = None

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraping incidenti CoratoLive")
    parser.add_argument("--max-pages", type=int, default=None, help="Limite di pagine per keyword/tag (None = tutte le pagine)")
    parser.add_argument("--limit", type=int, default=None, help="Limita numero record finali")
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Directory di output per i dataset",
    )
    parser.add_argument(
        "--dashboard-data",
        default="dashboard/public/data",
        help="Cartella in cui salvare i dati per la dashboard",
    )
    args = parser.parse_args()

    records = collect_incidents(max_pages=args.max_pages, limit=args.limit)
    outputs = save_dataset(records, args.output_dir)
    
    # Pulizia automatica del dataset
    if clean_dataset:
        logging.info("\n" + "=" * 80)
        logging.info("ESECUZIONE PULIZIA AUTOMATICA DATASET")
        logging.info("=" * 80)
        incidents_path = pathlib.Path(args.output_dir) / "incidents.json"
        clean_result = clean_dataset(
            incidents_path,
            incidents_path,  # Sovrascrive il file originale
            dry_run=False,
        )
        
        # Ricarica i record puliti
        with incidents_path.open("r", encoding="utf-8") as fh:
            records = json.load(fh)
        
        # Rigenera il dataset parquet con i dati puliti
        import pandas as pd
        df = pd.DataFrame(records)
        parquet_path = pathlib.Path(args.output_dir) / "incidents.parquet"
        df.to_parquet(parquet_path, index=False)
        
        logging.info("\n📊 REPORT PULIZIA:")
        logging.info("  Totale record prima: %d", clean_result["total"])
        logging.info("  Record mantenuti: %d (%.1f%%)", clean_result["kept"], 
                    (clean_result["kept"] / clean_result["total"] * 100) if clean_result["total"] > 0 else 0)
        logging.info("  Record rimossi: %d (%.1f%%)", clean_result["removed"],
                    (clean_result["removed"] / clean_result["total"] * 100) if clean_result["total"] > 0 else 0)
        if clean_result.get("removed_by_reason"):
            logging.info("  Dettaglio rimozioni:")
            for reason, count in clean_result["removed_by_reason"].items():
                if count > 0:
                    logging.info("    - %s: %d", reason, count)
        logging.info("=" * 80 + "\n")
    else:
        logging.warning("Script di pulizia non trovato, saltando la pulizia automatica")
    
    # Rigenera metriche con i dati puliti
    metrics = build_metrics(records)
    metrics_path = save_metrics(metrics, pathlib.Path(args.output_dir) / "metrics.json")

    dashboard_dir = pathlib.Path(args.dashboard_data)
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    with (dashboard_dir / "incidents.json").open("w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    with (dashboard_dir / "metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)

    logging.info("Dataset salvato: %s", outputs)
    logging.info("Metriche salvate: %s", metrics_path)
    logging.info("Dati pronti per dashboard in %s", dashboard_dir)


if __name__ == "__main__":
    main()
