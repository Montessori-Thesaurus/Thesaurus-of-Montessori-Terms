# Montessori Glossary - SKOS Thesaurus

A minimal glossary infrastructure that hosts a SKOS thesaurus for the Montessori vocabulary (vocabulary.montessoriglossary.org). Provides:

- FastAPI service with HTML UI and JSON API
- SKOS loading/serialization (TTL, JSON-LD, RDF/XML)
- CSV -> SKOS import script

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Import data

Place your CSV in `data/`. Example provided at `data/sample.csv` with headers:

- `prefLabel`
- `altLabel` (pipe `|` separated)
- `definition`
- optional `id`

Generate `data/vocabulary.ttl`:

```bash
python scripts/import_csv.py data/sample.csv
```

## Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` for the UI and `http://localhost:8000/api/docs` for API docs.

## API

- `GET /concepts?q=term` list/search
- `GET /concepts/{iri}` concept detail (URL-encode IRI)
- `GET /download.ttl|jsonld|xml` dataset downloads

## Config

Environment variables:

- `BASE_IRI` default `https://vocabulary.montessoriglossary.org/`
- `DATA_TTL_PATH` default `./data/vocabulary.ttl`
- `DEFAULT_LANGUAGE` default `en`

## Deploy

- Containerize with Uvicorn/Gunicorn
- Serve static templates from the app
- Mount or bake `data/vocabulary.ttl` into the image
