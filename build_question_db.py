#!/usr/bin/env python3
"""Build deduplicated PEIAR exam question database from source materials."""

import json
import re
import unicodedata
from pathlib import Path

EXTRACTED = Path(r"c:\Users\kubaj\Downloads\sczupryn.github.io-main\extracted_text")
OUTPUT = Path(r"c:\Users\kubaj\Downloads\sczupryn.github.io-main\baza_pytan_peiar.json")

QUESTION_START = re.compile(
    r"^(?:"
    r"(\d{1,3})[\.\)]\s+"           # 1. or 1)
    r"|Zad[-–]?\s*(\d{1,2})\.\s+"   # Zad-1.
    r"|[•]\s+"                     # bullet
    r"|(\d{1,3})\s+(?=[A-ZĄĆĘŁŃÓŚŹŻKt])"  # 1 Które...
    r")(.+)$",
    re.UNICODE,
)
OPTION_A = re.compile(r"^[\(\[]?([a-dA-D])[\)\]\.\)]\s*(.+)$")
OPTION_B = re.compile(r"^([a-dA-D])\)\s*(.+)$")
PAGE_MARK = re.compile(r"^--- PAGE \d+ ---$")

NOISE = (
    "notatki", "wykład", "wyk1", "wyk2", "wyk3", "wyk4", "wyk5",
    "co robi:", "zastosowanie:", "kiedy stosować:", "definicja:",
    "znaczenie:", "testy do analizy", "ignoruj numerację",
    "hipoteza zerowa(h", "p value", "p-value", "poisson modeluje",
    "tworzymy pary", "ortogonalne", "średnia …..", "h0 -",
)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    repl = str.maketrans("ąćęłńóśźż", "acelnoszz")
    text = text.translate(repl)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_noise(line: str) -> bool:
    s = line.strip().lower()
    if not s or PAGE_MARK.match(s):
        return True
    if re.fullmatch(r"\d{1,3}", s):
        return True
    if any(n in s for n in NOISE):
        return True
    if re.match(r"^[𝐹𝑥𝑑𝑙𝑎𝑛𝑘𝑤𝑎𝑟𝑡𝑜\s\-\+\=\;\,\.\(\)\[\]0-9/ϵ]+$", s):
        return True
    return False


def parse_option(line: str):
    s = line.strip()
    for pat in (OPTION_A, OPTION_B):
        m = pat.match(s)
        if m:
            return m.group(1).lower(), m.group(2).strip()
    return None, None


def looks_like_unlabeled_option(line: str, in_options: bool) -> bool:
    s = line.strip()
    if not s or len(s) > 130 or s.endswith(":"):
        return False
    if parse_option(s)[0]:
        return False
    if not in_options:
        return False
    # typical answer patterns
    if re.match(r"^(tak|nie|równości|dwóch|mediana|test |równość|do danych|gdy |przyjm|odrzuc|współ|średni|normaln|losow|moneta|kwadrat|zachodzi|nie można|nie zachodzi|co najmniej|dokładnie|o wartości)", s, re.I):
        return True
    if s[0].islower() and len(s.split()) <= 12:
        return True
    return False


MAX_OPTIONS = 6


def flush_question(q, source, out):
    if not q:
        return None
    stem = re.sub(r"\s+", " ", q.get("question", "")).strip()
    opts = q.get("options", [])
    if len(stem) < 12 or len(opts) < 2 or len(opts) > MAX_OPTIONS:
        return None
    seen = set()
    clean = []
    for o in opts:
        t = o["text"].strip()
        k = normalize_text(t)
        if k and k not in seen:
            seen.add(k)
            clean.append({"key": o["key"], "text": t})
    if len(clean) < 2:
        return None
    return {
        "question": stem,
        "options": clean,
        "sources": [source],
    }


def parse_block(lines: list[str], source: str):
    results = []
    q = None
    in_options = False

    def start_new(stem: str):
        nonlocal q, in_options
        prev = flush_question(q, source, results)
        if prev:
            results.append(prev)
        q = {"question": stem.strip(), "options": []}
        in_options = False

    for raw in lines:
        line = raw.strip()
        if is_noise(line):
            continue

        m = QUESTION_START.match(line)
        if m:
            stem = m.group(4).strip()
            start_new(stem)
            continue

        if not q:
            continue

        letter, opt_text = parse_option(line)
        if letter:
            q["options"].append({"key": letter, "text": opt_text})
            in_options = True
            continue

        if looks_like_unlabeled_option(line, in_options):
            key = chr(ord("a") + len(q["options"]))
            q["options"].append({"key": key, "text": line.strip()})
            continue

        if not in_options and len(q["options"]) == 0:
            q["question"] += " " + line.strip()
        elif in_options and len(line) < 80 and not line[0].isdigit():
            # continuation of last option
            q["options"][-1]["text"] += " " + line.strip()

    prev = flush_question(q, source, results)
    if prev:
        results.append(prev)
    return results


def extract_sections(text: str) -> list[str]:
    """Return lines belonging to question sections only."""
    lines = text.splitlines()
    out = []
    mode = "scan"
    for line in lines:
        low = line.lower().strip()
        if low in ("erni", "egzamin nr 1 (przykładowy)", "egzamin nr 1 (a)", "egzamin nr 1 (b)"):
            mode = "skip"
            continue
        if low.startswith("pytania z gpt") or low.startswith("dodatkowe pytania"):
            mode = "questions"
            continue
        if low.startswith("notatki") or low.startswith("test t-studenta") or low.startswith("testy do analizy"):
            mode = "skip"
            continue
        if re.match(r"^\d+\.\s", line) or re.match(r"^[•]\s", line) or re.match(r"^Zad[-–]", line, re.I):
            mode = "questions"
        if mode == "questions":
            out.append(line)
    return out if out else lines


# Hand-crafted from OCR scans (E1A, E1B, E2A) + egzamin przykładowy
OCR_EXAM_QUESTIONS = [
    {"question": "Mediana próbki losowej 2,4,9,2,5 wynosi liczba", "options": [{"key": "a", "text": "2"}, {"key": "b", "text": "3"}, {"key": "c", "text": "3.5"}, {"key": "d", "text": "4"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,3,4,4,6,7. Wartość F(5) wynosi wówczas", "options": [{"key": "a", "text": "0.5"}, {"key": "b", "text": "0.66"}, {"key": "c", "text": "0.33"}, {"key": "d", "text": "0.83"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Liczba serii w próbce losowej 15,9,5,12,1,3,8,4 względem jej mediany wynosi", "options": [{"key": "a", "text": "5"}, {"key": "b", "text": "4"}, {"key": "c", "text": "3"}, {"key": "d", "text": "6"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "W teście Kruskala-Wallisa połączonym próbkom x=c(0,2,7), y=c(-4,5), z=c(-2,1,8) przypisano rangi. Ranga -2 wynosi wówczas", "options": [{"key": "a", "text": "4"}, {"key": "b", "text": "5"}, {"key": "c", "text": "2"}, {"key": "d", "text": "3"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Wynikiem range(c(2,1,3,4,9)) w programie R jest", "options": [{"key": "a", "text": "1 9"}, {"key": "b", "text": "9 1"}, {"key": "c", "text": "2 9"}, {"key": "d", "text": "1 4"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Pierwsza próbka liczy 3 elementy, jej średnia wynosi 6. Druga próbka składa się z 5 elementów, jej średnia wynosi 8. Zatem średnia połączonych próbek wynosi", "options": [{"key": "a", "text": "7"}, {"key": "b", "text": "7.25"}, {"key": "c", "text": "8"}, {"key": "d", "text": "nie można wyznaczyć"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Niech X będzie zmienną losową o rozkładzie normalnym ze średnią 10 i wariancją 9. Wówczas P(X < 2) obliczymy w R za pomocą", "options": [{"key": "a", "text": "dnorm(2,10,3)"}, {"key": "b", "text": "pnorm(2,10,3)"}, {"key": "c", "text": "qnorm(2,10,3)"}, {"key": "d", "text": "pnorm(2,10,9)"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Współczynnik korelacji Kendalla τ dla obserwacji (1,2), (2,1), (3,5), (4,2) wynosi", "options": [{"key": "a", "text": "0.66"}, {"key": "b", "text": "0.33"}, {"key": "c", "text": "0.16"}, {"key": "d", "text": "0.45"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "W modelu regresji liniowej Y = β₀ + β₁X₁ + ε otrzymano reszty: -3, -2, 0, 1, 4. Estymowaną wartością nieznanej wariancji modelu jest więc", "options": [{"key": "a", "text": "7.5"}, {"key": "b", "text": "10"}, {"key": "c", "text": "30"}, {"key": "d", "text": "15"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Do obserwacji (-2,-1), (0,2), (1,0), (3,2), (4,2), (6,1) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt", "options": [{"key": "a", "text": "(0,1)"}, {"key": "b", "text": "(-1,1)"}, {"key": "c", "text": "(3,2)"}, {"key": "d", "text": "(2,1)"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Wynikiem rank(c(7,0,2,-1,3)) w programie R jest", "options": [{"key": "a", "text": "4 1 3 2 5"}, {"key": "b", "text": "5 2 3 1 4"}, {"key": "c", "text": "5 2 3 4 1"}, {"key": "d", "text": "5 3 2 1 4"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Na wykresach ramkowych (boxplot) za wartości odstające uznaje się takie, których odległość od kwartyli wynosi co najmniej", "options": [{"key": "a", "text": "1.5*IQR"}, {"key": "b", "text": "2*IQR"}, {"key": "c", "text": "2.5*IQR"}, {"key": "d", "text": "3*IQR"}], "sources": ["E1Arozw-2-1.pdf", "Zdaj_Niezdaja (1).pdf"]},
    {"question": "Analiza wariancji dotyczy weryfikacji hipotezy równości", "options": [{"key": "a", "text": "średnich"}, {"key": "b", "text": "wariancji"}, {"key": "c", "text": "rozkładów"}, {"key": "d", "text": "median"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Test serii można wykorzystać do weryfikacji hipotezy dotyczącej", "options": [{"key": "a", "text": "równości średnich"}, {"key": "b", "text": "równości wariancji"}, {"key": "c", "text": "równości rozkładów"}, {"key": "d", "text": "równości proporcji"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "W regresji liniowej jedną z miar dopasowania modelu do danych jest", "options": [{"key": "a", "text": "współczynnik korelacji"}, {"key": "b", "text": "współczynnik determinacji"}, {"key": "c", "text": "wartość dźwigni"}, {"key": "d", "text": "kurtoza"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Chcemy zbadać, czy pewna cecha ma rozkład normalny. Użyjemy w tym celu funkcji", "options": [{"key": "a", "text": "rnorm()"}, {"key": "b", "text": "dnorm()"}, {"key": "c", "text": "chisq.test()"}, {"key": "d", "text": "aov()"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Rozkład Fishera-Snedecora to rozkład ilorazu dwóch niezależnych zmiennych losowych o rozkładzie", "options": [{"key": "a", "text": "normalnym"}, {"key": "b", "text": "Studenta"}, {"key": "c", "text": "chi-kwadrat"}, {"key": "d", "text": "wykładniczym"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Za pomocą funkcji SIGN.test() można zweryfikować hipotezę dotyczącą", "options": [{"key": "a", "text": "kurtozy"}, {"key": "b", "text": "wariancji"}, {"key": "c", "text": "mediany"}, {"key": "d", "text": "średniej"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "W prawie Benforda prawdopodobieństwo wystąpienia cyfry 1 na pierwszym miejscu znaczącej wynosi", "options": [{"key": "a", "text": "log₁₀2"}, {"key": "b", "text": "log₂10"}, {"key": "c", "text": "log₁₀(1/log₁₀10)"}, {"key": "d", "text": "log₁₀(log₁₀10)"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "W celu weryfikacji hipotezy dotyczącej równości średnich w dwóch populacjach wykorzystamy funkcję", "options": [{"key": "a", "text": "mean()"}, {"key": "b", "text": "tsum.test()"}, {"key": "c", "text": "prop.test()"}, {"key": "d", "text": "var.test()"}], "sources": ["E1Arozw-2-1.pdf"]},
    {"question": "Kwartylem górnym próbki losowej 5,2,1,7,14,8,12 jest liczba", "options": [{"key": "a", "text": "10"}, {"key": "b", "text": "12"}, {"key": "c", "text": "14"}, {"key": "d", "text": "8"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,0,2,2,2,3,5. Wartość F(4) wynosi wówczas", "options": [{"key": "a", "text": "0.85"}, {"key": "b", "text": "0.12"}, {"key": "c", "text": "0.28"}, {"key": "d", "text": "0.71"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Liczba serii w próbce losowej 15,0,4,6,8,2,11,10 względem jej mediany wynosi", "options": [{"key": "a", "text": "4"}, {"key": "b", "text": "5"}, {"key": "c", "text": "6"}, {"key": "d", "text": "7"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "W teście Kruskala-Wallisa połączonym próbkom x=c(8,4,1), y=c(3,5), z=c(-2,0,7) przypisano rangi. Ranga 0 wynosi wówczas", "options": [{"key": "a", "text": "7"}, {"key": "b", "text": "6"}, {"key": "c", "text": "2"}, {"key": "d", "text": "4"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Wynikiem cummax(c(2,3,-1,4,0,5)) w programie R jest", "options": [{"key": "a", "text": "2 3 3 4 4 5"}, {"key": "b", "text": "2 3 3 3 4 5"}, {"key": "c", "text": "2 3 3 4 4 5"}, {"key": "d", "text": "2 3 4 4 4 5"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Pierwsza próbka liczy 3 elementy, jej wariancja wynosi 2. Druga próbka składa się z 4 elementów, jej wariancja wynosi 8. Zatem wariancja połączonych próbek wynosi", "options": [{"key": "a", "text": "nie można wyznaczyć bez średnich"}, {"key": "b", "text": "5"}, {"key": "c", "text": "10"}, {"key": "d", "text": "8"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Niech X będzie zmienną losową o rozkładzie Poissona ze średnią 3. Wówczas P(X=4) obliczymy w R za pomocą", "options": [{"key": "a", "text": "ppois(4,3)"}, {"key": "b", "text": "qpois(4,3)"}, {"key": "c", "text": "dpois(4,3)"}, {"key": "d", "text": "rpois(4,3)"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Współczynnik korelacji Kendalla τ dla obserwacji (3,2), (4,3), (5,2), (6,4) wynosi", "options": [{"key": "a", "text": "0.33"}, {"key": "b", "text": "0.66"}, {"key": "c", "text": "0.5"}, {"key": "d", "text": "0.16"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "W modelu regresji liniowej Y = β₀ + β₁X₁ + ε otrzymano reszty: -4, -2, 0, 1, 5. Estymowaną wartością nieznanej wariancji modelu jest więc", "options": [{"key": "a", "text": "11.5"}, {"key": "b", "text": "15.33"}, {"key": "c", "text": "9.2"}, {"key": "d", "text": "46"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Do obserwacji (-3,1), (0,0), (1,1), (3,3), (4,5) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt", "options": [{"key": "a", "text": "(-1,1)"}, {"key": "b", "text": "(2,4)"}, {"key": "c", "text": "(1,2)"}, {"key": "d", "text": "(4,5)"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Wynikiem pmax(c(4,0,6), c(3,2,7)) w programie R jest", "options": [{"key": "a", "text": "4 2 7"}, {"key": "b", "text": "4 0 7"}, {"key": "c", "text": "6 2 7"}, {"key": "d", "text": "4 2 6"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "W celu weryfikacji hipotezy dotyczącej równości wariancji w trzech populacjach wykorzystamy funkcję", "options": [{"key": "a", "text": "var()"}, {"key": "b", "text": "var.test()"}, {"key": "c", "text": "bartlett.test()"}, {"key": "d", "text": "aov()"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Test Shapiro-Wilka służy do weryfikacji hipotezy dotyczącej", "options": [{"key": "a", "text": "równości średnich"}, {"key": "b", "text": "równości wariancji"}, {"key": "c", "text": "normalności rozkładu"}, {"key": "d", "text": "losowości próby"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Błędem I-go rodzaju nazywamy sytuację, w której", "options": [{"key": "a", "text": "przyjmujemy hipotezę prawdziwą"}, {"key": "b", "text": "odrzucamy hipotezę prawdziwą"}, {"key": "c", "text": "przyjmujemy hipotezę fałszywą"}, {"key": "d", "text": "odrzucamy hipotezę fałszywą"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "W modelu regresji Y = β₀ + β₁X + ε estymator parametru β₁, czyli β̂₁, ma rozkład", "options": [{"key": "a", "text": "normalny"}, {"key": "b", "text": "chi-kwadrat"}, {"key": "c", "text": "Fishera-Snedecora"}, {"key": "d", "text": "Studenta"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Chcemy zbadać, czy pewna cecha ma rozkład wykładniczy. Użyjemy w tym celu funkcji", "options": [{"key": "a", "text": "rnorm()"}, {"key": "b", "text": "rexp()"}, {"key": "c", "text": "dnorm()"}, {"key": "d", "text": "pexp()"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Chcemy zbadać, czy pewna cecha ma rozkład normalny. Użyjemy w tym celu funkcji", "options": [{"key": "a", "text": "chisq.test()"}, {"key": "b", "text": "dnorm()"}, {"key": "c", "text": "aov()"}, {"key": "d", "text": "lillie.test()"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Zmienne losowe X, Y są niezależne i mają rozkłady normalne. Ponadto X ma średnią 6 i wariancję 10, a Y średnią 3 i wariancję 4. Zatem X−Y ma rozkład normalny ze średnią 3 i wariancją", "options": [{"key": "a", "text": "6"}, {"key": "b", "text": "14"}, {"key": "c", "text": "3"}, {"key": "d", "text": "9"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "W celu weryfikacji hipotezy dotyczącej równości średnich w trzech populacjach wykorzystamy funkcję", "options": [{"key": "a", "text": "aov()"}, {"key": "b", "text": "tsum.test()"}, {"key": "c", "text": "t.test()"}, {"key": "d", "text": "mean()"}], "sources": ["E1Brozw-1-1.pdf"]},
    {"question": "Odchylenie ćwiartkowe próbki losowej -1,14,16,6,8,0,2 wynosi", "options": [{"key": "a", "text": "2"}, {"key": "b", "text": "2.5"}, {"key": "c", "text": "3"}, {"key": "d", "text": "1.5"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,0,2,2,3,3,7,9. Wartość F(3) wynosi wówczas", "options": [{"key": "a", "text": "0.875"}, {"key": "b", "text": "0.5"}, {"key": "c", "text": "0.75"}, {"key": "d", "text": "0.625"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Liczba serii w próbce losowej 15,1,8,3,9,4,12,5 względem jej mediany wynosi", "options": [{"key": "a", "text": "3"}, {"key": "b", "text": "4"}, {"key": "c", "text": "5"}, {"key": "d", "text": "6"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Dane 1,1,2,4,6,6,8,9 pogrupowano w klasy o granicach 0.5,10. Średnia danych zgrupowanych wynosi zatem", "options": [{"key": "a", "text": "4.625"}, {"key": "b", "text": "5"}, {"key": "c", "text": "4"}, {"key": "d", "text": "6"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Wynikiem mean(c(2,0,4,NA,NA)) w programie R jest", "options": [{"key": "a", "text": "2"}, {"key": "b", "text": "NA"}, {"key": "c", "text": "1.5"}, {"key": "d", "text": "6/4"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Wynikiem sort(c(3,0,1,NA,NA)) w programie R jest", "options": [{"key": "a", "text": "0 1 3 NA NA"}, {"key": "b", "text": "3 1 0 NA NA"}, {"key": "c", "text": "0 1 3 3 1 0 NA NA"}, {"key": "d", "text": "1 0 3 NA NA"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "W programie R tworzymy obiekt h=hist(c(1,1,2,3,5,8)). Obiekt ten jest", "options": [{"key": "a", "text": "wektorem"}, {"key": "b", "text": "listą"}, {"key": "c", "text": "tablicą"}, {"key": "d", "text": "ramką danych"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Próbka losowa ma średnią 6, medianę 4 i wariancję 4. Współczynnik asymetrii Pearsona tej próbki wynosi więc", "options": [{"key": "a", "text": "0"}, {"key": "b", "text": "1"}, {"key": "c", "text": "2"}, {"key": "d", "text": "-1"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Współczynnik korelacji Kendalla τ dla obserwacji (2,2), (3,3), (4,3), (5,4) wynosi", "options": [{"key": "a", "text": "0.83"}, {"key": "b", "text": "0.16"}, {"key": "c", "text": "0.33"}, {"key": "d", "text": "0.45"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "W modelu regresji liniowej Y = β₀ + β₁X₁ + β₂X₂ + ε otrzymano reszty: -4,-3,-1,1,2,5. Estymowaną wartością nieznanej wariancji modelu jest więc", "options": [{"key": "a", "text": "14"}, {"key": "b", "text": "11.2"}, {"key": "c", "text": "18.66"}, {"key": "d", "text": "56"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Do obserwacji (-2,-1), (0,2), (2,5), (3,2), (4,2), (5,2) dopasowano prostą regresji metodą najmniejszych kwadratów. Prosta ta przechodzi więc przez punkt", "options": [{"key": "a", "text": "(0,1)"}, {"key": "b", "text": "(-1,1)"}, {"key": "c", "text": "(2,2)"}, {"key": "d", "text": "(3,2)"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Za pomocą funkcji ks.test() można zweryfikować hipotezę dotyczącą równości", "options": [{"key": "a", "text": "dwóch rozkładów"}, {"key": "b", "text": "dwóch wariancji"}, {"key": "c", "text": "dwóch średnich"}, {"key": "d", "text": "dwóch proporcji"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "W analizie wariancji zakłada się, że badana cecha w populacjach ma rozkład", "options": [{"key": "a", "text": "Studenta"}, {"key": "b", "text": "normalny"}, {"key": "c", "text": "chi-kwadrat"}, {"key": "d", "text": "Fishera-Snedecora"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Za pomocą funkcji wilcox.test() można zweryfikować hipotezę dotyczącą równości", "options": [{"key": "a", "text": "dwóch wariancji"}, {"key": "b", "text": "dwóch median"}, {"key": "c", "text": "kurtoz"}, {"key": "d", "text": "współczynników asymetrii"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Błędem II-go rodzaju nazywamy sytuację, w której", "options": [{"key": "a", "text": "przyjmujemy hipotezę prawdziwą"}, {"key": "b", "text": "odrzucamy hipotezę prawdziwą"}, {"key": "c", "text": "przyjmujemy hipotezę fałszywą"}, {"key": "d", "text": "odrzucamy hipotezę fałszywą"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Miara skośności Bowleya próbki losowej -1,14,16,6,8,0,2 wynosi", "options": [{"key": "a", "text": "0.1"}, {"key": "b", "text": "0.5"}, {"key": "c", "text": "1"}, {"key": "d", "text": "2"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Wariancja zmiennej losowej X o rozkładzie chi-kwadrat wynosi 20. Zatem X ma rozkład chi-kwadrat z", "options": [{"key": "a", "text": "20 stopniami swobody"}, {"key": "b", "text": "16 stopniami swobody"}, {"key": "c", "text": "10 stopniami swobody"}, {"key": "d", "text": "40 stopniami swobody"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Chcemy zbadać, czy współczynnik korelacji dwóch cech jest istotnie różny od zera. Użyjemy w tym celu funkcji", "options": [{"key": "a", "text": "cor()"}, {"key": "b", "text": "cor.test()"}, {"key": "c", "text": "HZ.test()"}, {"key": "d", "text": "skewness()"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Za pomocą funkcji prop.test() można zweryfikować hipotezę dotyczącą", "options": [{"key": "a", "text": "kurtozy"}, {"key": "b", "text": "wskaźnika struktury"}, {"key": "c", "text": "mediany"}, {"key": "d", "text": "średniej"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Zmienna losowa X ma rozkład normalny ze średnią 2 i wariancją 3. Zatem zmienna losowa Z = 2X - 1 ma rozkład normalny ze średnią 3 i wariancją", "options": [{"key": "a", "text": "6"}, {"key": "b", "text": "12"}, {"key": "c", "text": "5"}, {"key": "d", "text": "13"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Jeśli hipoteza zerowa jest prawdziwa, to rozkład p-wartości związany z tą hipotezą jest", "options": [{"key": "a", "text": "wykładniczy"}, {"key": "b", "text": "normalny"}, {"key": "c", "text": "jednostajny"}, {"key": "d", "text": "chi-kwadrat"}], "sources": ["E2A(rozw)-1.pdf"]},
    {"question": "Histogram pewnej próbki wygląda następująco. Wynika stąd, że dla tej próbki losowej", "options": [{"key": "a", "text": "mediana jest raczej większa od średniej"}, {"key": "b", "text": "mediana jest w przybliżeniu równa średniej"}, {"key": "c", "text": "mediana jest raczej mniejsza od średniej"}, {"key": "d", "text": "nie można ocenić"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Wynikiem diff(c(1,0,2,3,-1)) w programie R jest", "options": [{"key": "a", "text": "-1 2 1 -4"}, {"key": "b", "text": "1 2 1 4"}, {"key": "c", "text": "1 -2 -1 4"}, {"key": "d", "text": "-3"}], "sources": ["Egzamin1(przykładowy).pdf"]},
]


def dedupe_key(q: dict) -> str:
    stem = normalize_text(q["question"])
    opts = tuple(sorted(normalize_text(o["text"]) for o in q["options"]))
    return stem + "||" + "|".join(opts)


def merge(a: dict, b: dict) -> dict:
    a["sources"] = sorted(set(a.get("sources", []) + b.get("sources", [])))
    if len(b["question"]) > len(a["question"]):
        a["question"] = b["question"]
    return a


def parse_zdaj(lines: list[str], source: str):
    """Parser for Zdaj_Niezdaja format: numbered question + unlabeled options."""
    results = []
    q = None
    collecting_opts = False

    def finish():
        nonlocal q, collecting_opts
        item = flush_question(q, source, results)
        if item:
            results.append(item)
        q = None
        collecting_opts = False

    def add_unlabeled(line: str):
        key = chr(ord("a") + len(q["options"]))
        q["options"].append({"key": key, "text": line.strip()})

    for raw in lines:
        line = raw.strip()
        if is_noise(line) or PAGE_MARK.match(line):
            continue
        if re.match(r"^\d+\s*$", line) or line.startswith("gdzie:") or line.startswith("Najpierw"):
            continue
        if re.match(r"^[𝐹𝑥]", line):
            continue
        if line.startswith("Równość ") or line.startswith("Dwóch ") or " - " in line and line.endswith("."):
            continue

        m = re.match(r"^(\d{1,2})\.\s+(.+)$", line)
        if m:
            finish()
            q = {"question": m.group(2).strip(), "options": []}
            collecting_opts = False
            continue

        if not q:
            continue

        letter, opt = parse_option(line)
        if letter:
            q["options"].append({"key": letter, "text": opt})
            collecting_opts = True
            continue

        if len(line) < 130 and not line.endswith(":") and not line[0].isdigit():
            if collecting_opts or len(q["options"]) > 0:
                add_unlabeled(line)
                collecting_opts = True
            elif len(q["options"]) == 0:
                # first lines after stem are usually answers
                add_unlabeled(line)
                collecting_opts = True
            else:
                q["question"] += " " + line

    finish()
    return results


def parse_gpt_section(text: str, source: str):
    """Parse 'Pytania z GPT' numbered block only."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if "pytania z gpt" in l.lower()), None)
    if start is None:
        return []
    end = next((i for i, l in enumerate(lines[start + 1:], start + 1) if l.lower().startswith("notatki")), len(lines))
    return parse_block(lines[start:end], source)


EGZAMIN_PRZYKLADOWY = [
    {"question": "Medianą próbki losowej 1,2,3,4,5,6 jest liczba", "options": [{"key": "a", "text": "2"}, {"key": "b", "text": "1"}, {"key": "c", "text": "3"}, {"key": "d", "text": "3.5"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Niech F(x) będzie dystrybuantą empiryczną próbki losowej: -1,2,4,6. Wartość F(3.5) wynosi wówczas", "options": [{"key": "a", "text": "0.6"}, {"key": "b", "text": "0.5"}, {"key": "c", "text": "0.75"}, {"key": "d", "text": "0.25"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Na wykresie typu pudełkowego (boxplot) zaznaczane są", "options": [{"key": "a", "text": "mediana, średnia, xmax, xmin"}, {"key": "b", "text": "mediana, średnia, Q1, Q2, Q3"}, {"key": "c", "text": "mediana, Q1, Q3, xmax, xmin"}, {"key": "d", "text": "średnia, Q1, Q3, xmax, xmin"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Do zbadania równości dwóch wariancji wykorzystamy funkcję", "options": [{"key": "a", "text": "levene.test()"}, {"key": "b", "text": "var()"}, {"key": "c", "text": "fisher.test()"}, {"key": "d", "text": "sd()"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Test Kruskala-Wallisa służy do weryfikacji hipotezy dotyczącej", "options": [{"key": "a", "text": "równości średnich"}, {"key": "b", "text": "równości wariancji"}, {"key": "c", "text": "równości rozkładów"}, {"key": "d", "text": "równości proporcji"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Do zbadania niezależności statystycznej dwóch cech najlepiej wykorzystać funkcję", "options": [{"key": "a", "text": "indep()"}, {"key": "b", "text": "cor.test()"}, {"key": "c", "text": "chisq.test()"}, {"key": "d", "text": "cor()"}], "sources": ["Egzamin1(przykładowy).pdf"]},
    {"question": "Wynikiem c(1,2)+c(0,1,2) w programie R jest", "options": [{"key": "a", "text": "1 3"}, {"key": "b", "text": "1 3 3"}, {"key": "c", "text": "nie jest określone"}, {"key": "d", "text": "1 3 2"}], "sources": ["Egzamin1(przykładowy).pdf"]},
]


def load_all():
    all_q = list(OCR_EXAM_QUESTIONS)
    all_q.extend(EGZAMIN_PRZYKLADOWY)

    sources = [
        ("PEIAR_gotowiec-1.pdf.txt", "PEIAR_gotowiec-1.pdf"),
        ("erni.pdf.txt", "erni.pdf"),
    ]
    for fname, source in sources:
        path = EXTRACTED / fname
        if path.exists():
            text = path.read_text(encoding="utf-8")
            # core PEIAR block (before GPT section)
            core = text.split("Dodatkowe pytania")[0].split("Pytania z GPT")[0]
            all_q.extend(parse_block(core.splitlines(), source))
            all_q.extend(parse_gpt_section(text, source))

    zdaj = EXTRACTED / "Zdaj_Niezdaja_1.pdf.txt"
    if zdaj.exists():
        all_q.extend(parse_zdaj(zdaj.read_text(encoding="utf-8").splitlines(), "Zdaj_Niezdaja (1).pdf"))

    return all_q


def main():
    raw = load_all()
    db = {}
    for q in raw:
        k = dedupe_key(q)
        db[k] = merge(db[k], q) if k in db else q

    questions = sorted(db.values(), key=lambda x: normalize_text(x["question"]))
    for i, q in enumerate(questions, 1):
        q["id"] = i

    output = {
        "title": "Baza pytań PEIAR - Planowanie i Analiza Eksperymentu",
        "description": "Zdeduplikowana baza pytań egzaminacyjnych ze wszystkich materiałów źródłowych",
        "total_questions": len(questions),
        "sources": [
            "E1Arozw-2-1.pdf",
            "E1Brozw-1-1.pdf",
            "E2A(rozw)-1.pdf",
            "Egzamin1(przykładowy).pdf",
            "erni.pdf",
            "erni_merged.pdf",
            "erni_merged_merged.pdf",
            "Niezdaj, ale tym razem zdaj (1).docx",
            "PEIAR_gotowiec-1.pdf",
            "Zdaj_Niezdaja (1).pdf",
        ],
        "questions": questions,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Zapisano {len(questions)} unikalnych pytan")


if __name__ == "__main__":
    main()
