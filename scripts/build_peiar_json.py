#!/usr/bin/env python3
"""Convert baza_pytan_peiar.json to data/peiar.json with verified answer keys."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "baza_pytan_peiar.json"
OUT = ROOT / "data" / "peiar.json"
ZDAJ = ROOT / "extracted_text" / "Zdaj_Niezdaja_1.pdf.txt"
ERNI = ROOT / "extracted_text" / "erni.pdf.txt"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = text.replace("ł", "l").replace("ą", "a").replace("ę", "e")
    text = text.replace("ó", "o").replace("ś", "s").replace("ć", "c")
    text = text.replace("ń", "n").replace("ź", "z").replace("ż", "z")
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"[^a-z0-9+\-*/(). ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_numbers(raw: str) -> list[float]:
    raw = raw.replace("−", "-").replace("–", "-")
    parts = re.split(r"[,;\s]+", raw.strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p or p.lower() == "na":
            continue
        try:
            out.append(float(p))
        except ValueError:
            pass
    return out


def empirical_cdf(sample: list[float], x: float) -> float:
    n = len(sample)
    if n == 0:
        return 0.0
    return sum(1 for v in sample if v <= x) / n


def median_value(sample: list[float]) -> float:
    s = sorted(sample)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def count_runs_vs_median(sample: list[float]) -> int:
    med = median_value(sample)
    signs = []
    for v in sample:
        if v > med:
            signs.append(1)
        elif v < med:
            signs.append(-1)
        else:
            signs.append(0)
    runs = 1
    for i in range(1, len(signs)):
        if signs[i] != signs[i - 1]:
            runs += 1
    return runs


def match_numeric_option(value: float, options: list[dict], tol: float = 0.02) -> str | None:
    best = None
    best_diff = tol
    for opt in options:
        t = opt["text"].strip()
        m = re.search(r"-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?", t.replace(",", "."))
        if not m:
            continue
        try:
            if "/" in m.group(0):
                a, b = m.group(0).split("/")
                num = float(a.strip()) / float(b.strip())
            else:
                num = float(m.group(0))
        except ValueError:
            continue
        diff = abs(num - value)
        if diff < best_diff:
            best_diff = diff
            best = opt["text"]
    return best


def match_text_option(needle: str, options: list[dict]) -> str | None:
    nn = normalize(needle)
    for opt in options:
        if normalize(opt["text"]) == nn:
            return opt["text"]
    for opt in options:
        on = normalize(opt["text"])
        if nn in on or on in nn:
            return opt["text"]
    return None


def compute_answer(question: str, options: list[dict]) -> str | None:
    qn = normalize(question)

    m = re.search(
        r"dystrybuant[aą] empiryczn[aą].*?pro[bk]ki losowej[:\s]*([0-9,\.\-\s]+).*?f\s*\(\s*([0-9.+-]+)\s*\)",
        question,
        re.I | re.S,
    )
    if m:
        sample = parse_numbers(m.group(1))
        x = float(m.group(2))
        if sample:
            val = empirical_cdf(sample, x)
            hit = match_numeric_option(val, options)
            if hit:
                return hit

    m = re.search(r"median[aą] pr[oó]bki losowej[:\s]*([0-9,\.\-\s]+)", question, re.I)
    if m:
        sample = parse_numbers(m.group(1))
        if sample:
            val = median_value(sample)
            hit = match_numeric_option(val, options)
            if hit:
                return hit

    m = re.search(
        r"liczba serii.*?pr[oó]bce losowej[:\s]*([0-9,\.\-\s]+)",
        question,
        re.I | re.S,
    )
    if m:
        sample = parse_numbers(m.group(1))
        if sample:
            val = float(count_runs_vs_median(sample))
            hit = match_numeric_option(val, options)
            if hit:
                return hit

    if "pierwsza probka liczy 3 elementy" in qn and "srednia wynosi 6" in qn:
        return match_text_option("7.25", options)

    if "pierwsza probka liczy 3 elementy" in qn and "wariancja wynosi 2" in qn:
        return match_text_option("nie można", options) or match_text_option(
            "nie mozna wyznaczyc", options
        )

    if "x ma srednia 6 i wariancje 10" in qn and "y srednia 3 i wariancje 4" in qn:
        return match_text_option("14", options)

    if "zmienna losowa z = 2x - 1" in qn or "zmienna losowa z=2x-1" in qn:
        return match_text_option("12", options)

    return None


def parse_zdaj_keys() -> dict[str, str]:
    if not ZDAJ.exists():
        return {}
    text = ZDAJ.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("---")]
    keys: dict[str, str] = {}

    i = 0
    while i < len(lines):
        m = re.match(r"^(\d{1,2})\.\s+(.+)$", lines[i])
        if not m:
            i += 1
            continue
        q_parts = [m.group(2)]
        i += 1
        opts = []
        while i < len(lines) and not re.match(r"^\d{1,2}\.\s+", lines[i]):
            line = lines[i]
            if line.startswith("Równość ") or line.startswith("Dwóch ") or line.startswith("Analiza "):
                i += 1
                continue
            if line.startswith("Test ") and " - " in line:
                i += 1
                continue
            if line.startswith("cor()") or line.startswith("cor.test") or line.startswith("indep()"):
                i += 1
                continue
            if line.startswith("Mediana:") or line.startswith("Q1:"):
                break
            if len(opts) < 4 and len(line) < 120 and not line.startswith("Najpierw") and not line.startswith("gdzie:"):
                if not re.match(r"^[𝐹𝑥0-9/\s=;ϵ]+$", line):
                    opts.append(line)
            elif "Czyli wychodzi" in line or "Co daje nam" in line:
                num = re.search(r"=\s*([0-9.]+)", line)
                if num and opts:
                    keys[normalize(" ".join(q_parts))] = num.group(1)
                runs = re.search(r"(\d+)\s+serii", line)
                if runs and opts:
                    keys[normalize(" ".join(q_parts))] = runs.group(1)
            elif line.startswith("Aby obliczyć") or line.startswith("Jeśli p-wartość"):
                pass
            else:
                q_parts.append(line)
            i += 1

        qn = normalize(" ".join(q_parts))
        if qn in keys:
            continue

        # ustalone odpowiedzi z komentarzy Zdaj
        zdaj_fixed = {
            normalize("Test Kołmogorowa-Smirnowa wykorzystywany jest do weryfikacji hipotezy dotyczącej"): "równości rozkładów",
            normalize("Za pomocą funkcji t.test() można zweryfikować hipotezę dotyczącą równości"): "dwóch średnich",
            normalize("W modelu regresji liniowej zakłada się, że reszty mają rozkład normalny"): "o wartości oczekiwanej zero",
            normalize("Do zbadania niezależności statystycznej dwóch cech najlepiej wykorzystać funkcję"): "chisq.test()",
            normalize("Do zbadania niezależności dwóch cech najlepiej wykorzystać funkcję"): "chisq.test()",
            normalize("Histogram pewnej próbki losowej dany jest na poniższym rysunku Wynika stąd, że dla tej próbki losowej"): "mediana jest raczej mniejsza od średniej",
            normalize("W wykresach pudełkowych (boxplots) za wartości odstające uznaje się takie, dla których"): "odległość od kwartyli wynosi co najmniej 1.5 IQR",
            normalize("Mocą testu nazywamy prawdopodobieństwo"): "nie popełnienia błędu II rodzaju",
            normalize("Liczba serii liczonych względem mediany w próbce losowej −2, 3, 5, 1, 9, 6, 10, −8 wynosi"): "5",
            normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej 2, 0, 2, −1, 5 Wówczas F(4) wynosi"): "0.8",
            normalize("Oto dwa kwadraty łacińskie rzędu 3 Wynika stąd, że"): "kwadraty te są ortogonalne",
            normalize("Czy mediana próbki losowej może być większa od jej średniej arytmetycznej?"): "tak",
            normalize("Czy mediana próbki losowej może być mniejsza od jej średniej arytmetycznej?"): "tak",
            normalize("Najlepszy test do weryfikacji hipotezy o normalności danych to"): "test Shapiro-Wilka",
            normalize("Chcemy zbadać czy pewna cecha ma rozkład Poissona. Najlepszym testem do tego jest"): "test chi-kwadrat",
            normalize("W celu porównania dwóch średnich wykorzystamy"): "test Studenta",
            normalize("Medianą próbki losowej 0, 2, −1, 5, 4, 3 jest"): "2.5",
            normalize("Medianą próbki losowej 1, 2, 3, 4, 5, 6 jest liczba"): "3.5",
            normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej: −1, 2, 4, 6. Wartość F(3.5) wynosi wówczas"): "0.5",
            normalize("Na wykresie typu pudełkowego (\"boxplot\") zaznaczane są"): "mediana, Q1, Q3, xmax, xmin",
            normalize("Test Kruskala-Wallisa służy do weryfikacji hipotezy dotyczącej"): "równości rozkładów",
            normalize("Czy próbka losowa może mieć nieskończenie wiele median?"): "nie",
            normalize("Rozkład Snedecora wykorzystywany jest do weryfikacji hipotezy dotyczącej równości"): "dwóch wariancji",
            normalize("Do zbadania równości dwóch wariancji wykorzystamy funkcję"): "levene.test()",
            normalize("Wynikiem działania c(1,2)+c(0,1,2) w programie R jest"): "1 3 3",
            normalize("Oto wyniki 20 rzutów monetą (O-orzeł, R-reszka) O, O, O, O, O, O, O, O, O, O, R, R, R, R, R, R, R, R, R, R Wynika stąd, że"): "moneta najprawdopodobniej nie jest uczciwa",
        }
        for k, v in zdaj_fixed.items():
            if k in qn or qn in k:
                keys[qn] = v
                break

    return keys


def parse_erni_core_keys() -> dict[str, str]:
    """Pierwsze 17 pytań Erni z adnotacjami w pliku."""
    mapping = {
        normalize("Mocą testu nazywamy prawdopodobieństwo:"): "Nie popełnienia błędu II rodzaju",
        normalize("Oto wyniki 20 rzutów monetą"): "Moneta najprawdopodobniej nie jest uczciwa.",
        normalize("Rozkład Snedecora wykorzystywany jest do weryfikacji hipotezy dotyczącej równości:"): "Dwóch wariancji",
        normalize("W modelu regresji liniowej zakłada się, że reszty mają rozkład normalny."): "O wartości oczekiwanej zero",
        normalize("Medianą próbki losowej 0,2,-1,5,4,3 jest"): "2.5",
        normalize("Test Kołmogorowa-Smirnowa wykorzystywany jest do weryfikacji hipotezy dotyczącej"): "Równości rozkładów",
        normalize("Czy mediana próbki losowej może być większa od jej średniej arytmetycznej?"): "Tak",
        normalize("Histogram pewnej próbki losowej dany jest na poniższym rysunku. Wynika stąd, że dla tej próbki losowej"): "Mediana jest raczej mniejsza od średniej",
        normalize("Oto wyniki prawidłowo przeprowadzonej analizy wariancji dwuczynnikowej. Wynika stąd, że między czynnikami A oraz B"): "Nie zachodzi interakcja",
        normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej 2,0,2,-1,5. Wówczas F(4) wynosi"): "0.8",
        normalize("W wykresach pudełkowych (boxplots) za wartości"): "Odległość od kwartyli wynosi co najmniej 1.5 IQR",
        normalize("Jednym z warunków koniecznych do tego, aby zachodziło prawo Benforda jest to, żeby rząd wielkości zbioru był równy"): "Co najmniej 2",
        normalize("Liczba serii liczonych względem mediany w próbce losowej"): "5",
        normalize("Czy mediana próbki losowej może być mniejsza od jej średniej arytmetycznej?"): "Tak",
        normalize("Oto dwa kwadraty łacińskie rzędu 3. Wynika stąd, że"): "Kwadraty te są ortogonalne",
        normalize("Czy próbka losowa może mieć nieskończenie wiele median?"): "Nie",
        normalize("Za pomocą funkcji t.test() można zweryfikować hipotezę dotyczącą równości"): "Dwóch średnich",
    }
    return mapping


# Rozwiązania egzaminów A/B/2A (OCR + obliczenia + docx)
OCR_EXAM_KEYS: dict[str, str] = {
    normalize("Mediana próbki losowej 2,4,9,2,5 wynosi liczba"): "3",
    normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,3,4,4,6,7. Wartość F(5) wynosi wówczas"): "0.83",
    normalize("Liczba serii w próbce losowej 15,9,5,12,1,3,8,4 względem jej mediany wynosi"): "5",
    normalize("W teście Kruskala-Wallisa połączonym próbkom x=c(0,2,7), y=c(-4,5), z=c(-2,1,8) przypisano rangi. Ranga -2 wynosi wówczas"): "4",
    normalize("Wynikiem range(c(2,1,3,4,9)) w programie R jest"): "1 9",
    normalize("Pierwsza próbka liczy 3 elementy, jej średnia wynosi 6. Druga próbka składa się z 5 elementów, jej średnia wynosi 8. Zatem średnia połączonych próbek wynosi"): "7.25",
    normalize("Niech X będzie zmienną losową o rozkładzie normalnym ze średnią 10 i wariancją 9. Wówczas P(X < 2) obliczymy w R za pomocą"): "pnorm(2,10,3)",
    normalize("Współczynnik korelacji Kendalla τ dla obserwacji (1,2), (2,1), (3,5), (4,2) wynosi"): "0.33",
    normalize("W modelu regresji liniowej Y = β₀ + β₁X₁ + ε otrzymano reszty: -3, -2, 0, 1, 4. Estymowaną wartością nieznanej wariancji modelu jest więc"): "7.5",
    normalize("Do obserwacji (-2,-1), (0,2), (1,0), (3,2), (4,2), (6,1) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt"): "(1,2)",
    normalize("Wynikiem rank(c(7,0,2,-1,3)) w programie R jest"): "4 1 3 2 5",
    normalize("Za pomocą funkcji t.test() można zweryfikować hipotezę dotyczącą równości"): "dwóch średnich",
    normalize("Na wykresach ramkowych (boxplot) za wartości odstające uznaje się takie, których odległość od kwartyli wynosi co najmniej"): "1.5*IQR",
    normalize("Analiza wariancji dotyczy weryfikacji hipotezy równości"): "średnich",
    normalize("Test serii można wykorzystać do weryfikacji hipotezy dotyczącej"): "równości rozkładów",
    normalize("Współczynnik korelacji zmiennych losowych X i Y wynosi 0.5. Wynika stąd, że"): "Y = 2X - 1",
    normalize("Mocą testu statystycznego nazywa się prawdopodobieństwo"): "nie popełnienia błędu II rodzaju",
    normalize("W regresji liniowej jedną z miar dopasowania modelu do danych jest"): "współczynnik determinacji",
    normalize("Do zbadania tego, czy próbka ma charakter losowy, najlepiej wykorzystać funkcję"): "runs.test()",
    normalize("Rozkład Fishera-Snedecora to rozkład ilorazu dwóch niezależnych zmiennych losowych o rozkładzie"): "chi-kwadrat",
    normalize("Za pomocą funkcji SIGN.test() można zweryfikować hipotezę dotyczącą"): "mediany",
    normalize("W regresji liniowej zakłada się, że reszty (residuals) mają rozkład"): "normalny",
    normalize("W celu weryfikacji hipotezy dotyczącej równości średnich w dwóch populacjach wykorzystamy funkcję"): "tsum.test()",
    normalize("W prawie Benforda prawdopodobieństwo wystąpienia cyfry 1 na pierwszym miejscu znaczącej wynosi"): "log₁₀2",
    normalize("Kwartylem górnym próbki losowej 5,2,1,7,14,8,12 jest liczba"): "12",
    normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,0,2,2,2,3,5. Wartość F(4) wynosi wówczas"): "0.85",
    normalize("Liczba serii w próbce losowej 15,0,4,6,8,2,11,10 względem jej mediany wynosi"): "5",
    normalize("W teście Kruskala-Wallisa połączonym próbkom x=c(8,4,1), y=c(3,5), z=c(-2,0,7) przypisano rangi. Ranga 0 wynosi wówczas"): "6",
    normalize("Wynikiem cummax(c(2,3,-1,4,0,5)) w programie R jest"): "2 3 3 4 4 5",
    normalize("Pierwsza próbka liczy 3 elementy, jej wariancja wynosi 2. Druga próbka składa się z 4 elementów, jej wariancja wynosi 8. Zatem wariancja połączonych próbek wynosi"): "nie można wyznaczyć bez średnich",
    normalize("Niech X będzie zmienną losową o rozkładzie Poissona ze średnią 3. Wówczas P(X=4) obliczymy w R za pomocą"): "dpois(4,3)",
    normalize("Współczynnik korelacji Kendalla τ dla obserwacji (3,2), (4,3), (5,2), (6,4) wynosi"): "0.33",
    normalize("W modelu regresji liniowej Y = β₀ + β₁X₁ + ε otrzymano reszty: -4, -2, 0, 1, 5. Estymowaną wartością nieznanej wariancji modelu jest więc"): "15.33",
    normalize("Do obserwacji (-3,1), (0,0), (1,1), (3,3), (4,5) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt"): "(1,2)",
    normalize("Wynikiem pmax(c(4,0,6), c(3,2,7)) w programie R jest"): "4 2 7",
    normalize("W celu weryfikacji hipotezy dotyczącej równości wariancji w trzech populacjach wykorzystamy funkcję"): "bartlett.test()",
    normalize("Test Shapiro-Wilka służy do weryfikacji hipotezy dotyczącej"): "normalności rozkładu",
    normalize("Do zbadania niezależności statystycznej dwóch cech najlepiej wykorzystać funkcję"): "fisher.test()",
    normalize("Współczynnik korelacji zmiennych losowych X i Y wynosi 0.4. Wynika stąd, że"): "Y = 1 + 2X",
    normalize("Błędem I-go rodzaju nazywamy sytuację, w której"): "odrzucamy hipotezę prawdziwą",
    normalize("W modelu regresji Y = β₀ + β₁X + ε estymator parametru β₁, czyli β̂₁, ma rozkład"): "normalny",
    normalize("Chcemy zbadać, czy pewna cecha ma rozkład wykładniczy. Użyjemy w tym celu funkcji"): "rexp()",
    normalize("Rozkład Fishera-Snedecora wykorzystywany jest do weryfikacji hipotezy dotyczącej równości"): "dwóch wariancji",
    normalize("W celu weryfikacji hipotezy dotyczącej równości średnich w trzech populacjach wykorzystamy funkcję"): "aov()",
    normalize("Odchylenie ćwiartkowe próbki losowej -1,14,16,6,8,0,2 wynosi"): "2.5",
    normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,0,2,2,3,3,7,9. Wartość F(3) wynosi wówczas"): "0.75",
    normalize("Liczba serii w próbce losowej 15,1,8,3,9,4,12,5 względem jej mediany wynosi"): "4",
    normalize("Dane 1,1,2,4,6,6,8,9 pogrupowano w klasy o granicach 0.5,10. Średnia danych zgrupowanych wynosi zatem"): "4.625",
    normalize("Wynikiem mean(c(2,0,4,NA,NA)) w programie R jest"): "2",
    normalize("Wynikiem sort(c(3,0,1,NA,NA)) w programie R jest"): "0 1 3 NA NA",
    normalize("W programie R tworzymy obiekt h=hist(c(1,1,2,3,5,8)). Obiekt ten jest"): "lista",
    normalize("Próbka losowa ma średnią 6, medianę 4 i wariancję 4. Współczynnik asymetrii Pearsona tej próbki wynosi więc"): "1",
    normalize("Współczynnik korelacji Kendalla τ dla obserwacji (2,2), (3,3), (4,3), (5,4) wynosi"): "0.83",
    normalize("W modelu regresji liniowej Y = β₀ + β₁X₁ + β₂X₂ + ε otrzymano reszty: -4,-3,-1,1,2,5. Estymowaną wartością nieznanej wariancji modelu jest więc"): "14",
    normalize("Do obserwacji (-2,-1), (0,2), (2,5), (3,2), (4,2), (5,2) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt"): "(3,2)",
    normalize("Za pomocą funkcji ks.test() można zweryfikować hipotezę dotyczącą równości"): "dwóch rozkładów",
    normalize("Na wykresach pudełkowych (boxplot) zaznaczane są domyślnie"): "mediana, Q1, Q3, xmax, xmin",
    normalize("W analizie wariancji zakłada się, że badana cecha w populacjach ma rozkład"): "normalny",
    normalize("Za pomocą funkcji wilcox.test() można zweryfikować hipotezę dotyczącą równości"): "dwóch median",
    normalize("Współczynnik korelacji zmiennych losowych X i Y wynosi 0 (zero). Wynika stąd, że"): "X i Y są nieskorelowane",
    normalize("Błędem II-go rodzaju nazywamy sytuację, w której"): "przyjmujemy hipotezę fałszywą",
    normalize("Miara skośności Bowleya próbki losowej -1,14,16,6,8,0,2 wynosi"): "0.5",
    normalize("Wariancja zmiennej losowej X o rozkładzie chi-kwadrat wynosi 20. Zatem X ma rozkład chi-kwadrat z"): "20 stopniami swobody",
    normalize("Chcemy zbadać, czy współczynnik korelacji dwóch cech jest istotnie różny od zera. Użyjemy w tym celu funkcji"): "cor.test()",
    normalize("Jeśli hipoteza zerowa jest prawdziwa, to rozkład p-wartości związany z tą hipotezą jest"): "jednostajny",
    normalize("Medianą próbki losowej 1,2,3,4,5,6 jest liczba"): "3.5",
    normalize("Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,2,4,6. Wartość F(3.5) wynosi wówczas"): "0.5",
    normalize("Do zbadania równości dwóch wariancji wykorzystamy funkcję"): "levene.test()",
    normalize("Wynikiem c(1,2)+c(0,1,2) w programie R jest"): "1 3 3",
    normalize("Wynikiem diff(c(1,0,2,3,-1)) w programie R jest"): "-1 2 1 -4",
}

# Pytania GPT / ogólne (pewne odpowiedzi)
GPT_KEYS: dict[str, str] = {
    normalize("Które z poniższych stwierdzeń definiuje błąd I rodzaju?"): "Odrzucamy hipotezę zerową H0, gdy jest ona w rzeczywistości prawdziwa",
    normalize("Które z poniższych stwierdzeń definiuje błąd II rodzaju?"): "Nieodrzucenie hipotezy zerowej H0, gdy jest ona w rzeczywistości fałszywa",
    normalize("Które z poniższych stwierdzeń definiuje błąd typu I?"): "Odrzucamy hipotezę zerową H0, gdy jest ona w rzeczywistości prawdziwa",
    normalize("Co to jest błąd II rodzaju?"): "Nieodrzucenie hipotezy zerowej, gdy jest ona fałszywa",
    normalize("Co oznacza poziom istotności alfa w teście statystycznym?"): "Prawdopodobieństwo popełnienia błędu I rodzaju",
    normalize("W jakim celu stosuje się test t Studenta?"): "Do porównania dwóch średnich",
    normalize("Co oznacza wartość P w teście statystycznym?"): "Prawdopodobieństwo uzyskania wyników równych lub bardziej ekstremalnych od obserwowanych, przy założeniu prawdziwości hipotezy zerowej",
    normalize("Który z poniższych naukowców jest uważany za pioniera nowoczesnego planowania eksperymentów?"): "Ronald Fisher",
    normalize("Do jakiego rodzaju danych stosuje się test chi-kwadrat?"): "Do danych kategorycznych",
    normalize("Które z poniższych jest przykładem danych kategorycznych?"): "Kolor oczu",
    normalize("Jaki test statystyczny stosuje się do analizy dwóch zmiennych kategorycznych?"): "Test chi-kwadrat",
    normalize("Jakie jest prawdopodobieństwo uzyskania orła w rzucie symetryczną monetą?"): "0.50",
    normalize("Jakie jest prawdopodobieństwo wyrzucenia pary orzeł-orzeł (O,O) w pojedynczym rzucie dwoma monetami?"): "0.25",
    normalize("W eksperymencie rzucamy trzema niezależnymi monetami. Jakie jest prawdopodobieństwo wyrzucenia dokładnie jednego orła?"): "0.375",
    normalize("Jakie jest prawdopodobieństwo wyrzucenia co najmniej jednego orła w dwóch rzutach monetą?"): "0.75",
    normalize("Jakie jest prawdopodobieństwo wyrzucenia liczby 6 w pojedynczym rzucie sześcienną kostką do gry?"): "0.1667",
    normalize("Jakie jest prawdopodobieństwo, że z talii 52 kart wyciągniesz kartę asa?"): "0.077",
    normalize("Co zakłada hipoteza zerowa w teście statystycznym?"): "Brak różnic lub efektu",
    normalize("Co oznacza hipoteza alternatywna w teście statystycznym?"): "Istnienie różnic lub efektu",
    normalize("Co zakłada hipoteza alternatywna w teście statystycznym?"): "Że badana cecha X różni się od rozkładu opisanego w hipotezie zerowej",
    normalize("Jakie jest znaczenie wartości P < 0.05 w teście statystycznym?"): "Wynik jest statystycznie istotny",
    normalize("W jakiej sytuacji test statystyczny ma największą moc?"): "Gdy poziom istotności jest wysoki, np. 10%",
    normalize("W jakim celu stosuje się funkcję lm() w R?"): "Do dopasowania modelu liniowego",
    normalize("Jaką funkcję w R należy użyć, aby obliczyć korelację między dwiema zmiennymi?"): "cor()",
    normalize("Która z poniższych funkcji w R jest używana do obliczania mediany?"): "median()",
    normalize("Jaką funkcję w R należy użyć, aby utworzyć wykres pudełkowy?"): "boxplot()",
    normalize("Jaką funkcję w R należy użyć, aby utworzyć wykres punktowy?"): "plot()",
    normalize("Jaki jest cel testu ANOVA?"): "Do porównania średnich więcej niż dwóch grup",
    normalize("Który z poniższych jest testem nieparametrycznym?"): "Test Kruskala-Wallisa",
    normalize("W jakiej sytuacji stosuje się test Wilcoxona?"): "Gdy dane nie są normalnie rozłożone",
    normalize("Co to jest przedział ufności?"): "Zakres wartości, w którym z określonym prawdopodobieństwem znajduje się prawdziwa wartość parametru populacji",
    normalize("Co oznacza odchylenie standardowe?"): "Miara rozproszenia danych wokół średniej",
    normalize("Która funkcja w R jest używana do obliczania odchylenia standardowego?"): "sd()",
    normalize("Co oznacza test dwustronny?"): "Test, który sprawdza, czy średnia próbki jest różna od określonej wartości w obu kierunkach",
    normalize("Która z poniższych metod jest używana do analizy zależności między dwiema zmiennymi liczbowymi?"): "Analiza regresji liniowej",
    normalize("Co oznacza termin \"wartość oczekiwana\"?"): "Średnia ważona wszystkich możliwych wartości",
    normalize("Co oznacza współczynnik korelacji Pearsona?"): "Miara siły i kierunku liniowej zależności między dwiema zmiennymi",
    normalize("Który z poniższych jest testem parametrycznym?"): "Test t Studenta",
    normalize("Co oznacza współczynnik determinacji R2?"): "Miara, jak dobrze model dopasowuje się do danych",
    normalize("Co oznacza termin \"próba losowa\" w statystyce?"): "Próba wybrana w taki sposób, że każda jednostka ma równą szansę bycia wybraną",
    normalize("Jak nazywa się test, w którym kobieta twierdziła, że potrafi po smaku rozpoznać kolejność dodawania herbaty i mleka?"): "Test lady tasting tea",
    normalize("Jaki rozkład ma liczba odgadniętych prawidłowo filiżanek herbaty w teście lady tasting tea"): "Rozkład hipergeometryczny",
    normalize("Który z poniższych rozkładów jest stosowany do modelowania liczby kropelek na jednostkę długości śladu cząstki w komorze Wilsona?"): "Rozkład Poissona",
    normalize("Który z poniższych rozkładów jest stosowany do modelowania liczby zdarzeń w danym przedziale czasu?"): "Rozkład Poissona",
    normalize("Jakie są wymagania dotyczące próbki w teście chi-kwadrat?"): "Próba musi być wystarczająco duża i losowa",
    normalize("Jakie są wymagania dotyczące liczebności próby w teście skuteczności szczepionki?"): "Próbka musi być duża i różnorodna",
    normalize("Kiedy różnica między dwiema grupami w eksperymencie jest uznawana za istotną?"): "Gdy nie mogła być spowodowana czynnikami losowymi",
    normalize("Jakie jest znaczenie mocy testu w kontekście skuteczności szczepionki"): "Moc testu określa prawdopodobieństwo nie popełnienia błędu II rodzaju",
}


def lookup_answer(question: str, options: list[dict]) -> str | None:
    qn = normalize(question)

    computed = compute_answer(question, options)
    if computed:
        return computed

    all_keys = {}
    all_keys.update(parse_erni_core_keys())
    all_keys.update(parse_zdaj_keys())
    all_keys.update(OCR_EXAM_KEYS)
    all_keys.update(GPT_KEYS)

    # dokładne dopasowanie pytania
    if qn in all_keys:
        return match_text_option(all_keys[qn], options)

    # dopasowanie po fragmencie (najdłuższy klucz wygrywa)
    best_key = None
    for key in all_keys:
        if key in qn or qn in key:
            if best_key is None or len(key) > len(best_key):
                best_key = key
    if best_key:
        return match_text_option(all_keys[best_key], options)

    return None


def mark_answers(question: str, options: list[dict]) -> list[dict] | None:
    correct_text = lookup_answer(question, options)
    if not correct_text:
        return None
    answers = []
    matched = False
    for opt in options:
        is_correct = normalize(opt["text"]) == normalize(correct_text)
        if is_correct:
            matched = True
        answers.append({"text": opt["text"], "correct": is_correct})
    if not matched:
        return None
    return answers


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    questions_out = []
    skipped = []

    for q in data["questions"]:
        answers = mark_answers(q["question"], q["options"])
        if not answers:
            skipped.append(q["question"])
            continue
        questions_out.append({"question": q["question"], "answers": answers})

    out = {
        "id": "peiar",
        "name": "Planowanie i Analiza Eksperymentu (PEIAR)",
        "description": "Egzamin — pytania wielokrotnego wyboru (zaznacz jedną poprawną odpowiedź). 1 pkt za trafienie.",
        "questions": questions_out,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    subjects_path = ROOT / "data" / "subjects.json"
    subjects = json.loads(subjects_path.read_text(encoding="utf-8"))
    for s in subjects:
        if s["id"] == "peiar":
            s["questionCount"] = len(questions_out)
    subjects_path.write_text(json.dumps(subjects, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Zapisano {len(questions_out)} pytan do {OUT}")
    if skipped:
        print(f"Pominieto {len(skipped)} pytan bez klucza")


if __name__ == "__main__":
    main()
