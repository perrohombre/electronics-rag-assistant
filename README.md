# Electronics RAG Assistant

Projekt jest prototypem asystenta zakupowego dla scenariusza e-commerce, zbudowanym w architekturze Retrieval-Augmented Generation (RAG). Aktualna wersja systemu obsługuje domenę laptopów i pozwala wyszukiwać produkty na podstawie zapytań w języku polskim, np. `laptop do 4000 zł do programowania`, `laptop gamingowy` albo `Apple do nauki`.

Celem projektu jest sprawdzenie, czy połączenie ekstrakcji jawnych warunków z wyszukiwaniem semantycznym po opisach produktów pozwala generować odpowiedzi bardziej zgodne z realnym katalogiem niż klasyczny chatbot oparty wyłącznie na modelu językowym.

## Aktualny Stan Prac

W obecnej wersji przygotowano działający lokalnie pipeline RAG dla laptopów:

- utworzono własny dataset laptopów na podstawie danych z kategorii laptopów w Media Expert,
- zapisano dane w pliku CSV z polskimi nagłówkami i cenami w PLN,
- dodano ręcznie opracowaną kolumnę `opis_semantyczny`, która opisuje zastosowanie laptopa w języku naturalnym,
- zaimplementowano importer CSV do lokalnej bazy SQLite,
- dodano normalizację parametrów technicznych, m.in. ceny, RAM, SSD, przekątnej ekranu, odświeżania i informacji o dedykowanej karcie graficznej,
- przygotowano indeksowanie produktów w Qdrant na podstawie embeddingów tekstu `nazwa + opis_semantyczny`,
- zaimplementowano analizę zapytania użytkownika z użyciem modelu LLM i structured output,
- zaimplementowano wyszukiwanie w modelu: jawne filtry metadanych -> semantic search po przefiltrowanych produktach,
- dodano endpointy FastAPI do importu katalogu, indeksowania, wyszukiwania i generowania odpowiedzi,
- dodano prosty interfejs Streamlit do testowania systemu,
- przygotowano testy jednostkowe dla normalizacji, repozytorium, analizy zapytań, indeksowania, wyszukiwania i API.

Aktualny dataset zawiera 150 laptopów.

## Architektura Rozwiązania

System działa w następującym przepływie:

1. Użytkownik wpisuje zapytanie w języku polskim.
2. Moduł analizy zapytania wyciąga wyłącznie jawne, twarde warunki, np. maksymalną cenę, markę, minimalną ilość RAM lub SSD.
3. Backend waliduje wyciągnięte warunki względem lokalnego katalogu produktów.
4. Qdrant wykonuje wyszukiwanie semantyczne tylko na produktach spełniających twarde filtry.
5. Najlepsze wyniki są przekazywane do modułu odpowiedzi.
6. Asystent generuje krótką odpowiedź po polsku wyłącznie na podstawie odnalezionych rekordów.

Przykład:

```text
Zapytanie: laptop do 4000 zł do programowania
Filtr jawny: cena_pln <= 4000
Semantyka: "do programowania" jest obsługiwana przez embedding opisu semantycznego
Wynik: top produkty z katalogu spełniające budżet i semantycznie pasujące do zastosowania
```

System nie luzuje automatycznie twardych filtrów. Jeżeli użytkownik poda warunki niemożliwe do spełnienia w obecnym datasie, system zwraca informację o braku produktów zamiast generować nieistniejącą rekomendację.

## Dane

Źródłem danych jest lokalny plik:

```text
data/raw/mediaexpert_laptops.csv
```

Najważniejsze pola datasetu:

- `identyfikator_zrodla`
- `sku`
- `nazwa`
- `marka`
- `cena_pln`
- `dostepnosc`
- `url`
- `procesor`
- `ram`
- `dysk_ssd`
- `dysk_hdd`
- `karta_graficzna`
- `ekran`
- `system_operacyjny`
- `opis`
- `opis_semantyczny`

Kolumna `opis_semantyczny` jest obecnie głównym źródłem informacji semantycznej dla wyszukiwania wektorowego. Parametry techniczne pozostają metadanymi wykorzystywanymi do filtrowania.

## Technologie

- Python
- FastAPI
- SQLite
- Qdrant
- OpenAI API
- Streamlit
- Playwright
- pytest
- ruff

## Uruchomienie Lokalne

Instalacja projektu:

```bash
python -m pip install -e ".[dev]"
```

Wymagane zmienne środowiskowe:

```bash
export OPENAI_API_KEY="..."
export QDRANT_URL="http://127.0.0.1:6333"
export DATASET_CSV_PATH="data/raw/mediaexpert_laptops.csv"
export CATALOG_DB_PATH="data/catalog.db"
```

Uruchomienie Qdrant:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Import danych do SQLite:

```bash
import-laptops
```

Budowa indeksu wektorowego:

```bash
index-laptops
```

Uruchomienie API:

```bash
uvicorn mediaexpert_laptops.rag.app:app --reload --host 127.0.0.1 --port 8000
```

Przykładowe zapytanie:

```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"laptop do 4000 zł do programowania","limit":5}'
```

Uruchomienie UI:

```bash
streamlit run src/mediaexpert_laptops/rag/ui.py
```

Jeżeli komendy `import-laptops` lub `index-laptops` nie są dostępne, należy najpierw zainstalować projekt w trybie editable komendą `python -m pip install -e ".[dev]"`.

## Scraper

Projekt zawiera scraper kategorii laptopów Media Expert oparty o Playwright. Można go uruchomić komendą:

```bash
scrape-mediaexpert-laptops --pages all --delay 1.0 --output data/raw/mediaexpert_laptops.csv
```

W praktyce strona może stosować zabezpieczenia antybotowe, dlatego scraper traktowany jest jako narzędzie do przygotowania datasetu, a nie jako produkcyjny mechanizm stałej synchronizacji danych.

## Testy

Uruchomienie testów:

```bash
pytest
```

Sprawdzenie jakości kodu:

```bash
ruff check .
```

Ostatnio sprawdzony stan:

```text
19 passed
All checks passed
```

## Plan Dalszych Prac

Najbliższe kierunki rozwoju projektu:

- rozbudowa interfejsu użytkownika tak, aby pokazywał pełny przebieg retrievalu krok po kroku,
- dodanie widoku debugowego pokazującego wyciągnięte filtry, liczbę produktów po filtrowaniu, wyniki Qdrant i kontekst przekazywany do LLM,
- przygotowanie zestawu ewaluacyjnego zapytań testowych i raportu jakości odpowiedzi,
- rozszerzenie datasetu o większą liczbę laptopów,
- późniejsze rozszerzenie systemu o kolejne kategorie produktów, np. monitory, słuchawki lub smartfony,
- dopracowanie odpowiedzi asystenta pod kątem wyjaśnialności rekomendacji.

## Status Projektu

Projekt znajduje się na etapie działającego prototypu lokalnego. Obecna wersja potwierdza techniczną wykonalność podejścia RAG dla danych produktowych oraz stanowi bazę do dalszej ewaluacji jakości wyszukiwania i rekomendacji.
