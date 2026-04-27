# Electronics RAG Assistant

Nowy start projektu.

Pierwszy krok to lokalny dataset laptopów tworzony z listingów Media Expert.
Scraper pobiera HTML kategorii, wyciąga karty produktów i zapisuje polski snapshot CSV.
Plik `data/raw/mediaexpert_laptops.csv` w repo jest tylko małym seedem startowym.

## Scraping laptopów

Najpierw zainstaluj projekt w aktywnym środowisku:

```bash
python -m pip install -e ".[dev]"
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
