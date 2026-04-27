# Electronics RAG Assistant

Nowy start projektu.

Pierwszy krok to lokalny dataset laptopów tworzony z listingów Media Expert.
Scraper pobiera HTML kategorii, wyciąga karty produktów i zapisuje polski snapshot CSV.

## Scraping laptopów

```bash
python -m mediaexpert_laptops.scraper --pages 1 --output data/raw/mediaexpert_laptops.csv
```

Żeby pobrać wszystkie wykryte strony listingu:

```bash
python -m mediaexpert_laptops.scraper --pages all --delay 1.0 --output data/raw/mediaexpert_laptops.csv
```

Jeśli Media Expert zwróci challenge Cloudflare dla automatycznego pobrania, zapisz HTML strony
z przeglądarki i użyj trybu lokalnego:

```bash
python -m mediaexpert_laptops.scraper --input-html data/raw/mediaexpert_laptops.html --output data/raw/mediaexpert_laptops.csv
```

Wynikowy CSV ma polskie nagłówki i ceny w PLN zgodnie ze źródłem.
