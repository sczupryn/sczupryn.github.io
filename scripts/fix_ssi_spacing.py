#!/usr/bin/env python3
"""Regenerate docs/data/ssi.json from source JS with spacing fixes."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "pytania_systemy_sztucznej_inteligencji.js"
OUT = ROOT / "docs" / "data" / "ssi.json"

PROTECTED = [
    "NumPy", "pandas", "DataFrame", "sklearn", "imblearn", "PowerShell",
    "read_csv", "groupby", "value_counts", "dropna", "describe", "astype",
    "reshape", "arange", "linspace", "asarray", "default_rng", "standard_normal",
    "One-vs-Rest", "One-vs-One", "cross-entropy", "log-loss", "K-Nearest",
    "Recursive Feature Elimination", "Box–Cox", "Yeo–Johnson", "Self-Supervised",
    "Semi-Supervised", "Unsupervised", "Federated Learning", "Transfer Learning",
    "Reinforcement Learning", "Policy gradient", "Q-learning", "Hello World",
    "requirements.txt", "people.csv", "Linear Regression", "Polynomial Features",
    "Random Forest", "StandardScaler", "MinMaxScaler", "RobustScaler",
    "Power Transformer", "Gaussian NB", "Bernoulli NB", "Linear SVC",
    "forward chaining", "backward chaining", "Local Outlier Factor",
    "median absolute deviation", "ColumnTransformer", "PolynomialFeatures",
    "RandomForestClassifier", "RandomForestRegressor", "LogisticRegression",
    "LinearRegression", "LinearSVC", "RobustScaler", "StandardScaler",
    "PowerTransformer", "Ordinal encoding", "Label encoding", "Hashing encoding",
    "One–hot encoding", "Yeo–Johnson", "Box–Cox", "Active Learning",
]

MANUAL: list[tuple[str, str]] = [
    ("charakterbehawioralnejdefinicji", "charakter behawioralnej definicji"),
    ("myślowego„chiński pokój”(Searle’a)", "myślowego „chiński pokój” (Searle’a)"),
    ("paradygmatów:nadzorowane", "paradygmatów: nadzorowane"),
    ("→uczenie", "→ uczenie"),
    ("obrazująszkodępotencjalnie", "obrazują szkodę potencjalnie wywołaną"),
    ("Definicjaagenta racjonalnegow", "Definicja agenta racjonalnego w"),
    ("Któreobszary i kompetencjesensownie", "Które obszary i kompetencje sensownie"),
    ("implikujerozumienia", "implikuje rozumienia"),
    ("któreNIEnależą", "które NIE należą"),
    ("semi-supervisedsą", "semi-supervised są"),
    ("zsklearn.", "z sklearn."),
    ("zsklearni", "z sklearn i"),
    ("σjest", "σ jest"),
    ("prognozyt", "prognozy t"),
    ("docelowey", "docelowe y"),
    ("revenue (w milionach) icount", "revenue (w milionach) i count"),
    ("Na N", "NaN"),
    ("Power Shell", "PowerShell"),
    ("Num Py", "NumPy"),
    ("Data Frame", "DataFrame"),
    ("Zpandas.", "Z pandas."),
    ("dfwybierz", "df wybierz"),
    ("Namei Ageoraz", "Name i Age oraz"),
    ("kolumnyNameiAgeoraz", "kolumny Name i Age oraz"),
    ("wiersze zAge", "wiersze z Age"),
    ("utworzyćpandas.", "utworzyć pandas."),
    ("DataFramez", "DataFrame z"),
    ("listnames,agesz", "list names, ages z"),
    ("szeregu czasowymdf", "szeregu czasowym df"),
    ("CSVpeople.csvdopandas.", "CSV people.csv do pandas."),
    ("DataFramei", "DataFrame i"),
    ("gruppandas.", "grup pandas."),
    ("dfwedługAge", "df według Age"),
    ("rozkładuN(0,1)", "rozkładu N(0,1)"),
    ("typufloat", "typu float"),
    ("naNumPy", "na NumPy"),
    ("porównująlistęikrotkę", "porównują listę i krotkę"),
    ("operatorzeindladictsą", "operatorze in dla dict są"),
    ("opop,remove,clearsą", "o pop, remove, clear są"),
    ("startując odlst", "startując od lst"),
    ("dlavenvw", "dla venv w"),
    ("Jakwyłączyćaktywne", "Jak wyłączyć aktywne"),
    ("aktywujeśrodowiskoprojw", "aktywuje środowisko proj w"),
    ("poprawnie aktywujeśrodowiskoprojw", "poprawnie aktywuje środowisko proj w"),
    ("ocechach numerycznychijakościowychsą", "o cechach numerycznych i jakościowych są"),
    ("Czym jeststandaryzacjaz-score", "Czym jest standaryzacja z-score"),
    ("Transformacja Yeo–Johnsonwzględem", "Transformacja Yeo–Johnson względem"),
    ("żededuplikacjanie", "że deduplikacja nie"),
    ("byćniebezpiecznydla", "być niebezpieczny dla"),
    ("pomagająunikać wyciekuprzy", "pomagają unikać wycieku przy"),
    ("pomagająuniknąć wyciekui", "pomagają uniknąć wycieku i"),
    ("Powdrożeniu", "Po wdrożeniu"),
    ("omechanizmach brakówsą", "o mechanizmach braków są"),
    ("poprawnymistrategiami", "poprawnymi strategiami"),
    ("sąprawdziwe", "są prawdziwe"),
    ("oweakly", "o weakly"),
    ("z= (x−µ)/σ", "z=(x−µ)/σ"),
    ("Q 3−Q 1", "Q3−Q1"),
    ("log (x+ 1)", "log(x+1)"),
    ("g (n)", "g(n)"),
    ("h (n)", "h(n)"),
    ("f (n)", "f(n)"),
    ("Ov R", "OvR"),
    ("Ov O", "OvO"),
    ("np.L 2/L1", "np.L2/L1"),
    ("consistentw A*", "consistent w A*"),
    ("domyśl- nymi", "domyślnymi"),
    ("stratyL(θ)", "straty L(θ)"),
    ("obliczeniowejDL", "obliczeniowej DL"),
    ("mediachSI", "mediach SI"),
    ("wdrażanieSI", "wdrażanie SI"),
    ("modeliw", "modeli w"),
    ("zzasadą", "z zasadą"),
    ("szkodyprzy", "szkody przy"),
    ("(RL)jako", "(RL) jako"),
    ("wtransporcie", "w transporcie"),
    ("metodęappend", "metodę append"),
    ("elementów tablicya", "elementów tablicy a"),
    ("N(0,1)(rozkład", "N(0,1) (rozkład"),
    ("ztrain", "z train"),
]

CURATED_GLUE_STARTERS = """
występuje funkcja funkcję funkcji definicji definicję inteligencji charakter behawioralnej
energetyce obejmują kompetencje obszary nadzorowane nienadzorowane samonadzorowane
utrzymuje racjonalnego definicja agenta pętlę szkodę potencjalnie wywołaną
wymagania obliczeniowej niefunkcjonalne własności środowiska transportcie
definicję sztucznej klasyczny odpowiedzialne wdrażanie aktuatory kontekście
definiuje straty sztuce mediach ocenie modeli stronniczość wyłączyć aktywuje
konwertują porównują elementów tablicy odczytać liczność operatorze alternatywy
uzupełnienia zarządzaniu utworzyć właściwe przetwarzania logarytmowanie
zidentyfikować formaty jednostki strategiami uzupełniania usuwanie mechanizmach
wdrożeniu statystyki dyskretyzacja metody odstających uniknąć unikać dokładne
scenariuszach treningu maszynowe federacyjne wariancję selekcja redukcji
parametry hiperparametrów korzysta algorytmów hiperparametr encoding standaryzacja
deduplikacja interpolować duplikaty przekleństwie wycieku detekcji anomalii
tradycyjnego paradygmatów paradygmacie zasadą minimalizacji projektowaniu
należą pandas numpy dataframe sklearn venv windows typu float kolumny wiersze
według poprawnie aktywuje środowisko projektowanie selekcji cech
jednowymiarowych wielowymiarowych preprocessing outliery outlierów normalizacji
skalowania braków duplikatów duplikaty rekordów rekordy wartości odstających
wykrywania uzupełniania imputacja standaryzacji skalowanie cech
reprodukowalności eksperymentów underfittingu overfittingu stratyfikacji
sensownie mieszczą implikuje rozumienia paradygmatów hybrydowy symboliczny
działanie akcja środowisko modelu turinga definiowania minimalizacji
maksymalizacji klasyfikacji regresji uczeniu wzmocnieniem wzmocnienia
eksploracja eksploatacja percepcja planowania przeszukiwania heurystyki
reprezentacji wiedzy wnioskowania odróżnia ouczeniu jako które
porównują listę krotkę operatorze ind dict są startując
dadzą wynik wybierz zobaczyć podstawowe statystyki liczność grup
utworzyć dwóch list kolumnami typu cechy kiedy logarytmowanie
przekleństwie wymiarowości pomagają braki duplikaty wymagające
naniespójne formaty wymagające ujednolicenia ordinal hashing
standaryzacja label one encoding cechy transformacja względem
deduplikacja label encoding niebezpieczny unikać wycieku przy
kluczu skale wymagające braków usuwanie mechanizmach braków
wdrożeniu statystyki binning detekcji anomalii uniknąć wycieku
interpolować brakujące zadań typowe scenariuszach supervised
funkcjach treningu programowania tradycyjnego reprodukowalności
eksperymentów krzywe uczenia underfittingu transfer learning
opisuje maszynowe active learning samonadzorowane rodzaju etykiet
metryki jakości stratyfikacji celem typowego procesu rodzaje błędów
ryzyka przygotowania federacyjne federated learning rozpoznać nadmierną
wariancję selekcja redukcji wymiarowości parametry hiperparametrów
transfer częściowo nienadzorowane sposobami ograniczania weakly
techniki należą paradygmacie korzysta paradygmaty uczenia przypisano
przekleństwo algorytmów skalowanie oznacza hiperparametr
Czym jest Dobierz przetwarzania stwierdzenia przykłady praktyki
techniki sytuacje wskazują przykłady wskazują podejścia poprawne
""".split()

CODE_SPACE_FIXES = [
    (r"\.astype\s+\(", ".astype("),
    (r"\.reshape\s+\(", ".reshape("),
    (r"\.where\s+\(", ".where("),
    (r"\.query\s+\(", ".query("),
    (r"\.select\s+\(", ".select("),
    (r"\.mean\s+\(", ".mean("),
    (r"\.median\s+\(", ".median("),
    (r"\.average\s+\(\s*\)", ".average()"),
    (r"\.len\s+\(\s*\)", ".len()"),
    (r"\.count\s+\(", ".count("),
    (r"\.filter\s+\(", ".filter("),
    (r"\.unique\s+\(\s*\)", ".unique()"),
    (r"\.dropna\s+\(\s*\)", ".dropna()"),
    (r"\.value_counts\s+\(\s*\)", ".value_counts()"),
    (r"\.summary\s+\(\s*\)", ".summary()"),
    (r"\.describe\s+\(\s*\)", ".describe()"),
    (r"\.info\s+\(\s*\)", ".info()"),
    (r"\.values\s+\(\s*\)", ".values()"),
    (r"\.append\s+\(", ".append("),
    (r"\.extend\s+\(", ".extend("),
    (r"\.pop\s+\(", ".pop("),
    (r"\.remove\s+\(", ".remove("),
    (r"\.clear\s+\(", ".clear("),
    (r"\.add\s+\(", ".add("),
    (r"\.drop_duplicates\s+\(", ".drop_duplicates("),
    (r"\.duplicated\s+\(", ".duplicated("),
    (r"\.interpolate\s+\(", ".interpolate("),
    (r"\.binarize\s+\(", ".binarize("),
    (r"\.size\s+\(\s*\)", ".size()"),
    (r"numpy\.array\s+\(", "numpy.array("),
    (r"numpy\.float\s+\(", "numpy.float("),
    (r"numpy\.mean\s+\(", "numpy.mean("),
    (r"numpy\.sum\s+\(", "numpy.sum("),
    (r"numpy\.reshape\s+\(", "numpy.reshape("),
    (r"numpy\.arange\s+\(", "numpy.arange("),
    (r"numpy\.linspace\s+\(", "numpy.linspace("),
    (r"numpy\.asarray\s+\(", "numpy.asarray("),
    (r"numpy\.select\s+\(", "numpy.select("),
    (r"numpy\.random\.default_rng\s+\(\s*\)", "numpy.random.default_rng()"),
    (r"standard_normal\s+\(", "standard_normal("),
    (r"normal\s+\(loc", "normal(loc"),
    (r"uniform\s+\(0", "uniform(0)"),
    (r"pandas\.read_csv\s+\(", "pandas.read_csv("),
    (r"pandas\.load_csv\s+\(", "pandas.load_csv("),
    (r"pandas\.DataFrame\.read\s+\(", "pandas.DataFrame.read("),
    (r"pandas\.Series\s+\(", "pandas.Series("),
    (r"read_csv\s+\(", "read_csv("),
    (r"DataFrame\s+\(\{", "DataFrame({"),
    (r"from_dict\s+\(\{", "from_dict({"),
    (r"len\s+\(", "len("),
    (r"storeas\s+\(", "storeas("),
    (r"draw normal", "draw_normal"),
]

TOKEN_RE = re.compile(
    r"[A-Za-zÀ-žąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9][A-Za-zÀ-žąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9_./\\–—−+]*"
    r"|[()\[\]{}.,;:!?→–—−+]|[^\s]"
)


@lru_cache(maxsize=1)
def _glue_pattern() -> re.Pattern[str]:
    starters = sorted({w.lower() for w in CURATED_GLUE_STARTERS if len(w) >= 4}, key=len, reverse=True)
    return re.compile(rf"(?<=[a-ząćęłńóśźż])({'|'.join(re.escape(s) for s in starters)})", re.IGNORECASE)


@lru_cache(maxsize=1)
def _valid_tokens() -> set[str]:
    raw = SRC.read_text(encoding="utf-8")
    texts: list[str] = []
    for m in re.finditer(r'question:\s*"((?:[^"\\]|\\.)*)"', raw):
        texts.append(m.group(1))
    for m in re.finditer(r'text:\s*"((?:[^"\\]|\\.)*)"', raw):
        texts.append(m.group(1))

    glued_blacklist: set[str] = set()
    for t in texts:
        for run in re.findall(r'[^\s"„”(),.;:→\[\]{}\\/–—−+]+', t):
            if len(run) >= 12 and re.search(r"[a-ząćęłńóśźż]{4,}[a-ząćęłńóśźż]{4,}", run, re.I):
                glued_blacklist.add(run.lower())

    valid: set[str] = set()
    for t in texts:
        for token in re.split(r"[\s/(),.;:→\[\]{}–—−+]+", t):
            token = re.sub(r"^[„\"'(\[]+|[)\"'»\]]+$", "", token)
            if re.match(r"^[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,24}$", token):
                low = token.lower()
                if low not in glued_blacklist:
                    valid.add(low)
    return valid


def protect(text: str) -> tuple[str, list[str]]:
    saved: list[str] = []
    for term in sorted(PROTECTED, key=len, reverse=True):
        if term in text:
            idx = len(saved)
            placeholder = f"\x00P{idx}\x00"
            saved.append(term)
            text = text.replace(term, placeholder)
    return text, saved


def restore(text: str, saved: list[str]) -> str:
    for i, term in enumerate(saved):
        text = text.replace(f"\x00P{i}\x00", term)
    return text


def fix_glued_token(token: str) -> str:
    valid = _valid_tokens()
    if token.lower() in valid:
        return token
    if len(token) < 8 or not re.search(r"[a-ząćęłńóśźż]", token, re.I):
        return token

    text = token
    pattern = _glue_pattern()
    for _ in range(5):
        new = pattern.sub(r" \1", text)
        if new == text:
            break
        text = new
    return text


def fix_text(text: str) -> str:
    text, saved = protect(text)
    for old, new in sorted(MANUAL, key=lambda x: -len(x[0])):
        text = text.replace(old, new)

    text = re.sub(r"([a-ząćęłńóśźż])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s*→\s*", " → ", text)
    text = re.sub(r"([a-ząćęłńóśźż])„", r"\1 „", text)
    text = re.sub(r"”([a-ząćęłńóśźż\(])", r"” \1", text)
    text = re.sub(r"([a-ząćęłńóśźż])(SI|ML|DL|AI|RL|XAI)\b", r"\1 \2", text)
    text = re.sub(r"\b(SI|ML|DL|AI|RL|XAI)([a-ząćęłńóśźż])", r"\1 \2", text)

    parts = re.split(r"(\s+)", text)
    for i, part in enumerate(parts):
        if part and not part.isspace():
            parts[i] = fix_glued_token(part)
    text = "".join(parts)

    for old, new in sorted(MANUAL, key=lambda x: -len(x[0])):
        text = text.replace(old, new)

    text = restore(text, saved)
    for pattern, repl in CODE_SPACE_FIXES:
        text = re.sub(pattern, repl, text)
    return re.sub(r"  +", " ", text).strip()


def parse_js(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    blocks = re.findall(
        r'question:\s*"((?:[^"\\]|\\.)*)"\s*,\s*answers:\s*\[(.*?)\]\s*\}',
        raw,
        re.DOTALL,
    )
    questions = []
    for q_text, ans_block in blocks:
        answers = []
        for m in re.finditer(
            r'\{text:\s*"((?:[^"\\]|\\.)*)"\s*,\s*correct:\s*(true|false)\s*\}',
            ans_block,
        ):
            answers.append({"text": m.group(1), "correct": m.group(2) == "true"})
        questions.append({"question": q_text, "answers": answers})
    return questions


def main() -> None:
    questions = parse_js(SRC)
    for q in questions:
        q["question"] = fix_text(q["question"])
        for a in q["answers"]:
            a["text"] = fix_text(a["text"])

    data = {
        "id": "ssi",
        "name": "Systemy Sztucznej Inteligencji",
        "description": "Egzamin — 256 pytań wielokrotnego wyboru. 1 pkt za wszystkie poprawne odpowiedzi.",
        "questions": questions,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(questions)} questions to {OUT}")
    print(f"MANUAL replacements: {len(MANUAL)}")
    print(f"Curated glue starters: {len(set(CURATED_GLUE_STARTERS))}")


if __name__ == "__main__":
    main()
