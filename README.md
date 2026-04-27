# Electronics RAG Assistant

Lokalny prototyp RAG dla wyszukiwania laptopów z datasetu Media Expert.
Retrieval działa w modelu: jawne filtry z zapytania -> Qdrant semantic search po `opis_semantyczny`.

## RAG

Zainstaluj projekt i przygotuj env:

```bash
python -m pip install -e ".[dev]"
cp .env.example .env
```

Uzupełnij `OPENAI_API_KEY`, potem uruchom Qdrant:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Zaimportuj CSV do SQLite i zbuduj indeks Qdrant:

```bash
import-laptops
index-laptops
```

Uruchom API:

```bash
uvicorn mediaexpert_laptops.rag.app:app --reload --host 127.0.0.1 --port 8000
```

Przykładowe zapytanie:

```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"laptop do 4000 zł do programowania","limit":5}'
```

UI Streamlit:

```bash
streamlit run src/mediaexpert_laptops/rag/ui.py
```

## Dataset i scraping

Obecny dataset `data/raw/mediaexpert_laptops.csv` zawiera 150 laptopów i ręcznie dodaną
kolumnę `opis_semantyczny`, która jest głównym tekstem do embeddingów.

```bash
python -m playwright install chromium
```

Potem uruchom scraper przez entry point:

```bash
scrape-mediaexpert-laptops --pages 1 --output data/raw/mediaexpert_laptops.csv
```

Domyślnie scraper używa Playwrighta i otwiera Chromium w trybie headless. Jeśli chcesz
zobaczyć okno przeglądarki:

```bash
scrape-mediaexpert-laptops --pages 1 --headed --output data/raw/mediaexpert_laptops.csv
```

Alternatywnie, bez instalacji pakietu, ustaw `PYTHONPATH`:

```bash
PYTHONPATH=src python -m mediaexpert_laptops.scraper --pages 1 --output data/raw/mediaexpert_laptops.csv
```

Żeby pobrać wszystkie wykryte strony listingu:

```bash
scrape-mediaexpert-laptops --pages all --delay 1.0 --output data/raw/mediaexpert_laptops.csv
```

Jeśli Media Expert zwróci challenge Cloudflare dla automatycznego pobrania, zapisz HTML strony
z przeglądarki i użyj trybu lokalnego:

```bash
scrape-mediaexpert-laptops --input-html data/raw/mediaexpert_laptops.html --output data/raw/mediaexpert_laptops.csv
```

Wynikowy CSV ma polskie nagłówki i ceny w PLN zgodnie ze źródłem.

Jeśli po parsowaniu zapisanego HTML wynik ma tylko kilka produktów, zapisany plik HTML
najpewniej zawiera tylko fragment listingu. Pierwsza strona kategorii zwykle pokazuje
około 30 produktów, więc taki wynik oznacza problem z wejściowym HTML-em albo selekcją linków.

Jeśli Playwright także trafi na blokadę Cloudflare, uruchom komendę z `--headed` i sprawdź,
czy strona wymaga ręcznej weryfikacji w oknie przeglądarki.
