# Quiz egzaminacyjny

Statyczna strona quizu do nauki przed egzaminem.

## Lokalnie

```bash
cd docs
python3 -m http.server 8765
```

Otwórz http://localhost:8765

## GitHub Pages

1. Wypchnij repozytorium na GitHub.
2. W **Settings → Pages** ustaw **Source** na **GitHub Actions**.
3. Po pushu na `main` workflow `.github/workflows/pages.yml` opublikuje folder `docs/`.

## Zasady punktacji

Zgodnie z egzaminem: **1 punkt** tylko gdy zaznaczone są **wszystkie** poprawne odpowiedzi i **żadna** błędna.

## Historia i powtórka (localStorage)

Po każdej ukończonej sesji quiz zapisuje w **localStorage przeglądarki** (osobno dla każdego użytkownika/urządzenia):

- wynik ostatniej sesji,
- które pytania zostały źle,
- zaznaczone odpowiedzi.

Przy wyborze przedmiotu można uruchomić:

- **Pełny test** — wszystkie pytania,
- **Powtórka błędnych** — tylko pytania złe w ostatniej sesji (dostępne po pierwszym teście z błędami).

## Źródło pytań (SSI)

Tekst egzaminu z kluczem (■ poprawne, □ błędne) jest w `data/exam_clean.txt`.  
Po edycji tego pliku zregeneruj quiz:

```bash
python3 scripts/parse_exam.py
```

Skrypt tworzy `data/ssi.json`.

## Źródło pytań (PEIAR)

Pytania i poprawne odpowiedzi pochodzą z materiałów przesłanych przez użytkownika (obrazki z zaznaczonymi odpowiedziami).  
Aby zaktualizować quiz po dodaniu nowych pytań, edytuj `scripts/build_peiar_from_user.py` i uruchom:

```bash
python3 scripts/build_peiar_from_user.py
```

Skrypt tworzy `data/peiar.json` (bez duplikatów) i aktualizuje licznik w `data/subjects.json`.

## Dodawanie przedmiotów

1. Dodaj plik JSON w `data/` (wzoruj się na `ssi.json`).
2. Dodaj wpis w `data/subjects.json`.
