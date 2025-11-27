# Scraping Articoli Incidenti CoratoLive

Sistema completo per lo scraping, l'analisi e la visualizzazione di articoli relativi a incidenti dal sito CoratoLive.it.

## 📋 Descrizione

Questo progetto raccoglie automaticamente articoli di incidenti da CoratoLive.it utilizzando l'API WordPress, li pulisce, analizza e genera metriche statistiche. Include anche una dashboard interattiva per visualizzare i dati raccolti.

## 🏗️ Struttura del Progetto

```
.
├── src/                    # Codice sorgente Python
│   └── incidenti_scraping/ # Moduli per lo scraping
├── scripts/                # Script di utilità
│   ├── run_pipeline.py     # Esegue l'intera pipeline
│   └── clean_dataset.py    # Pulizia automatica dei dati
├── analysis/               # Moduli per l'analisi
│   └── metrics.py          # Calcolo delle metriche
├── dashboard/              # Dashboard React/TypeScript
│   └── src/                # Codice sorgente frontend
├── data/                   # Dati raccolti (JSON, Parquet)
└── notebooks/              # Jupyter notebooks per analisi

```

## 🚀 Installazione

### Prerequisiti

- Python 3.8+
- Node.js 18+
- npm o yarn

### Setup Python

```bash
# Crea un ambiente virtuale
python -m venv venv

# Attiva l'ambiente virtuale
# Su macOS/Linux:
source venv/bin/activate
# Su Windows:
venv\Scripts\activate

# Installa le dipendenze
pip install -r requirements.txt
```

### Setup Dashboard

```bash
cd dashboard
npm install
```

## 💻 Utilizzo

### Eseguire la Pipeline Completa

```bash
python scripts/run_pipeline.py
```

Opzioni disponibili:

- `--max-pages`: Limita il numero di pagine per keyword/tag (default: tutte)
- `--limit`: Limita il numero totale di record (default: tutti)
- `--output-dir`: Directory di output per i dataset (default: `data`)
- `--dashboard-data`: Cartella per i dati della dashboard (default: `dashboard/public/data`)

Esempio:

```bash
python scripts/run_pipeline.py --max-pages 5 --limit 100
```

### Avviare la Dashboard

```bash
cd dashboard
npm run dev
```

La dashboard sarà disponibile su `http://localhost:5173` (o la porta indicata da Vite).

### Build della Dashboard

```bash
cd dashboard
npm run build
```

I file compilati saranno nella cartella `dashboard/dist/`.

## 📊 Funzionalità

### Scraping

- Raccolta automatica di articoli da CoratoLive.it tramite WordPress REST API
- Filtraggio per keyword e tag relativi agli incidenti
- Estrazione di metadati (titolo, data, contenuto, URL, ecc.)

### Pulizia Dati

- Rimozione automatica di duplicati
- Filtraggio di articoli non rilevanti
- Normalizzazione del testo

### Analisi

- Calcolo di metriche statistiche
- Analisi temporale degli incidenti
- Generazione di report JSON

### Dashboard

- Visualizzazione interattiva dei dati
- Grafici e statistiche
- Filtri e ricerche

## 📦 Dipendenze

### Python

- `requests`: Per le richieste HTTP
- `pandas`: Per la manipolazione dei dati
- `beautifulsoup4`: Per il parsing HTML
- `python-dateutil`: Per la gestione delle date
- `unidecode`: Per la normalizzazione del testo
- `pyarrow`: Per il supporto Parquet

### Node.js

- `react`: Framework UI
- `recharts`: Libreria per grafici
- `date-fns`: Utilità per le date
- `vite`: Build tool

## 📝 Note

- Il progetto utilizza l'API pubblica di WordPress di CoratoLive.it
- I dati vengono salvati in formato JSON e Parquet
- La dashboard legge i dati dalla cartella `public/data/`

## 🔧 Sviluppo

### Struttura dei Moduli

- `incidenti_scraping.pipeline`: Logica principale di scraping
- `incidenti_scraping.wordpress_client`: Client per l'API WordPress
- `incidenti_scraping.text_utils`: Utilità per la manipolazione del testo
- `incidenti_scraping.config`: Configurazioni condivise
- `analysis.metrics`: Calcolo delle metriche statistiche

## 📄 Licenza

[Specificare la licenza se applicabile]

