#!/usr/bin/env python3
"""Build data/peiar.json from user-provided questions. Deduplicates by question text."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "peiar.json"
SUBJECTS = ROOT / "data" / "subjects.json"

# Each item: (question, [(answer_text, is_correct), ...])
RAW: list[tuple[str, list[tuple[str, bool]]]] = [
    # === Główna lista (1–17) ===
    ("Mocą testu nazywamy prawdopodobieństwo:", [
        ("nie popełnienia błędu I rodzaju", False),
        ("popełnienia błędu I rodzaju", False),
        ("nie popełnienia błędu II rodzaju", True),
        ("popełnienia błędu II rodzaju", False),
    ]),
    (
        "Oto wyniki 20 rzutów monetą (O-orzeł, R-reszka): "
        "O,O,O,O,O,O,O,O,O,O,R,R,R,R,R,R,R,R,R,R. Wynika stąd, że:",
        [
            ("moneta najprawdopodobniej nie jest uczciwa", False),
            ("nie można stwierdzić czy moneta jest uczciwa", False),
            ("moneta najprawdopodobniej jest uczciwa", True),
        ],
    ),
    ("Rozkład Snedecora wykorzystywany jest do weryfikacji hipotezy dotyczącej równości:", [
        ("dwóch średnich", False),
        ("dwóch median", False),
        ("dwóch wariancji", True),
        ("dwóch rozkładów", False),
    ]),
    ("W modelu regresji liniowej zakłada się, że reszty mają rozkład normalny", [
        ("o wartości oczekiwanej zero", True),
        ("o wartości oczekiwanej dodatniej", False),
        ("o wartości oczekiwanej ujemnej", False),
    ]),
    ("Medianą próbki losowej 0, 2, -1, 5, 4, 3 jest", [
        ("2.5", True),
        ("4", False),
        ("2", False),
        ("3", False),
    ]),
    ("Test Kołmogorowa-Smirnowa wykorzystywany jest do weryfikacji hipotezy dotyczącej", [
        ("równości wariancji", False),
        ("równości rozkładów", True),
        ("równości median", False),
        ("równości średnich", False),
    ]),
    ("Czy mediana próbki losowej może być większa od jej średniej arytmetycznej?", [
        ("tak", True),
        ("nie", False),
    ]),
    (
        "Histogram pewnej próbki losowej dany jest na poniższym rysunku. "
        "Wynika stąd, że dla tej próbki losowej",
        [
            ("mediana jest raczej większa od średniej", False),
            ("mediana jest równa średniej", False),
            ("mediana jest raczej mniejsza od średniej", True),
        ],
        "images/histogram-skewed.png",
    ),
    (
        "Oto wyniki prawidłowo przeprowadzonej analizy wariancji dwuczynnikowej "
        "(A: F=22.900, p=1.13e-05; B: F=0.305, p=0.7412; A:B: F=2.834, p=0.0552). "
        "Wynika stąd, że między czynnikami A oraz B",
        [
            ("zachodzi interakcja", False),
            ("nie można stwierdzić czy zachodzi interakcja", False),
            ("nie zachodzi interakcja", True),
        ],
    ),
    ("Niech F(x) będzie dystrybuantą empiryczną próbki losowej 2, 0, 2, -1, 5. Wówczas F(4) wynosi", [
        ("0.5", False),
        ("0.9", False),
        ("0.8", True),
        ("0.6", False),
    ]),
    ("W wykresach pudełkowych (boxplots) za wartości odstające uznaje się takie, dla których", [
        ("odległość od kwartyli wynosi co najmniej 3.5 IQR", False),
        ("odległość od kwartyli wynosi co najmniej 0.5 IQR", False),
        ("odległość od kwartyli wynosi co najmniej 1.5 IQR", True),
        ("odległość od kwartyli wynosi co najmniej 2.5 IQR", False),
    ]),
    (
        "Jednym z warunków koniecznych do tego, aby zachodziło prawo Benforda jest to, "
        "żeby rząd wielkości zbioru danych był równy",
        [
            ("co najmniej 3", True),
            ("co najmniej 2", False),
            ("dokładnie 3", False),
            ("co najmniej 4", False),
        ],
    ),
    ("Liczba serii liczonych względem mediany w próbce losowej -2, 3, 5, 1, 9, 6, 10, -8 wynosi", [
        ("4", False),
        ("8", False),
        ("5", True),
        ("6", False),
    ]),
    ("Czy mediana próbki losowej może być mniejsza od jej średniej arytmetycznej?", [
        ("tak", True),
        ("nie", False),
    ]),
    (
        "Oto dwa kwadraty łacińskie rzędu 3. Wynika stąd, że",
        [
            ("kwadraty te nie są ortogonalne", False),
            ("nie można stwierdzić czy kwadraty te są ortogonalne", False),
            ("kwadraty te są ortogonalne", True),
        ],
        "images/latin-squares.png",
    ),
    ("Czy próbka losowa może mieć nieskończenie wiele median?", [
        ("tak", False),
        ("nie", True),
    ]),
    ("Za pomocą funkcji t.test() można zweryfikować hipotezę dotyczącą równości", [
        ("dwóch wariancji", False),
        ("dwóch rozkładów", False),
        ("dwóch średnich", True),
    ]),
    # === Pytania GPT (1–55) ===
    ("Które z poniższych stwierdzeń definiuje błąd I rodzaju?", [
        ("Przyjmujemy hipotezę zerową H0, gdy jest ona w rzeczywistości fałszywa", False),
        ("Odrzucamy hipotezę zerową H0, gdy jest ona w rzeczywistości prawdziwa", True),
        ("Przyjmujemy hipotezę alternatywną H1, gdy jest ona w rzeczywistości fałszywa", False),
        ("Odrzucamy hipotezę alternatywną H1, gdy jest ona w rzeczywistości prawdziwa", False),
    ]),
    ("Które z poniższych stwierdzeń opisuje hipotezę zerową (H0)?", [
        ("Hipoteza zerowa zakłada, że badana cecha X ma rozkład normalny", True),
        ("Hipoteza zerowa zakłada, że badana cecha X ma dowolny rozkład", False),
        ("Hipoteza zerowa zakłada, że hipoteza alternatywna jest prawdziwa", False),
        ("Hipoteza zerowa zakłada, że badana cecha X ma nieznany rozkład", False),
    ]),
    ("Jakie jest znaczenie mocy testu w kontekście skuteczności szczepionki Polio?", [
        ("Moc testu określa prawdopodobieństwo odrzucenia hipotezy zerowej, gdy jest ona prawdziwa", False),
        ("Moc testu określa prawdopodobieństwo przyjęcia hipotezy zerowej, gdy jest ona fałszywa", False),
        ("Moc testu określa prawdopodobieństwo nie popełnienia błędu II rodzaju", True),
        ("Moc testu określa prawdopodobieństwo popełnienia błędu I rodzaju", False),
    ]),
    ("W jakiej sytuacji test statystyczny ma największą moc?", [
        ("Gdy poziom istotności jest wysoki, np. 10%", True),
        ("Gdy poziom istotności jest niski, np. 1%", False),
        ("Gdy poziom istotności jest umiarkowany, np. 5%", False),
        ("Gdy moc testu wynosi 0.5", False),
    ]),
    (
        "Jak nazywa się test, w którym kobieta twierdziła, że potrafi po smaku rozpoznać "
        "kolejność dodawania herbaty i mleka?",
        [
            ("Test chi-kwadrat", False),
            ("Test lady tasting tea", True),
            ("Test t Studenta", False),
            ("Test Kołmogorowa-Smirnowa", False),
        ],
    ),
    (
        "Jaki rozkład ma liczba odgadniętych prawidłowo filiżanek herbaty w teście lady tasting tea, "
        "przy założeniu prawdziwości hipotezy zerowej?",
        [
            ("Rozkład dwumianowy", False),
            ("Rozkład hipergeometryczny", True),
            ("Rozkład normalny", False),
            ("Rozkład Poissona", False),
        ],
    ),
    ("Do jakiego rodzaju danych stosuje się test chi-kwadrat?", [
        ("Do danych kategorycznych", True),
        ("Do danych ciągłych", False),
        ("Do danych binarnych", False),
        ("Do danych porządkowych", False),
    ]),
    (
        "Który z poniższych rozkładów jest stosowany do modelowania liczby kropelek "
        "na jednostkę długości śladu cząstki w komorze Wilsona?",
        [
            ("Rozkład normalny", False),
            ("Rozkład hipergeometryczny", False),
            ("Rozkład Poissona", True),
            ("Rozkład dwumianowy", False),
        ],
    ),
    ("Co zakłada hipoteza alternatywna w teście statystycznym?", [
        ("Że badana cecha X ma rozkład normalny", False),
        ("Że badana cecha X ma dowolny rozkład", False),
        ("Że badana cecha X różni się od rozkładu opisanego w hipotezie zerowej", True),
        ("Że badana cecha X jest zgodna z hipotezą zerową", False),
    ]),
    ("Jakie są wymagania dotyczące liczebności próby w teście skuteczności szczepionki?", [
        ("Próbka musi być mała i jednorodna", False),
        ("Próbka musi być duża i różnorodna", True),
        ("Próbka musi pochodzić z jednego regionu", False),
        ("Próbka musi być nieznana", False),
    ]),
    ("Który z poniższych naukowców jest uważany za pioniera nowoczesnego planowania eksperymentów?", [
        ("Gregor Mendel", False),
        ("Harold Jeffreys", False),
        ("Ronald Fisher", True),
        ("Karl Pearson", False),
    ]),
    ("Co oznacza wartość P w teście statystycznym?", [
        (
            "Prawdopodobieństwo uzyskania wyników równych lub bardziej ekstremalnych od obserwowanych, "
            "przy założeniu prawdziwości hipotezy zerowej",
            True,
        ),
        ("Prawdopodobieństwo, że hipoteza alternatywna jest prawdziwa", False),
        ("Prawdopodobieństwo, że hipoteza zerowa jest prawdziwa", False),
        ("Prawdopodobieństwo popełnienia błędu typu I", False),
    ]),
    ("Co to jest błąd II rodzaju?", [
        ("Odrzucenie hipotezy zerowej, gdy jest ona prawdziwa", False),
        ("Nieodrzucenie hipotezy zerowej, gdy jest ona fałszywa", True),
        ("Odrzucenie hipotezy alternatywnej, gdy jest ona prawdziwa", False),
        ("Nieodrzucenie hipotezy alternatywnej, gdy jest ona fałszywa", False),
    ]),
    ("Kiedy różnica między dwiema grupami w eksperymencie jest uznawana za istotną?", [
        ("Gdy nie mogła być spowodowana czynnikami losowymi", True),
        ("Gdy mogła być spowodowana czynnikami losowymi", False),
        ("Gdy różnica jest większa niż 10%", False),
        ("Gdy różnica jest mniejsza niż 5%", False),
    ]),
    ("Które z poniższych stwierdzeń definiuje błąd II rodzaju?", [
        ("Przyjmujemy hipotezę zerową H0, gdy jest ona w rzeczywistości fałszywa", False),
        ("Odrzucamy hipotezę zerową H0, gdy jest ona w rzeczywistości prawdziwa", False),
        ("Nieodrzucenie hipotezy zerowej H0, gdy jest ona w rzeczywistości fałszywa", True),
        ("Odrzucenie hipotezy alternatywnej H1, gdy jest ona w rzeczywistości prawdziwa", False),
    ]),
    ("Co oznacza poziom istotności alfa w teście statystycznym?", [
        (
            "Prawdopodobieństwo uzyskania wyników równych lub bardziej ekstremalnych od obserwowanych",
            False,
        ),
        ("Prawdopodobieństwo popełnienia błędu I rodzaju", True),
        ("Prawdopodobieństwo popełnienia błędu II rodzaju", False),
        ("Prawdopodobieństwo odrzucenia hipotezy alternatywnej", False),
    ]),
    ("W jakim celu stosuje się test t Studenta?", [
        ("Do porównania więcej niż dwóch grup", False),
        ("Do porównania dwóch średnich", True),
        ("Do analizy korelacji", False),
        ("Do analizy regresji", False),
    ]),
    ("Który z poniższych rozkładów jest stosowany do modelowania liczby zdarzeń w danym przedziale czasu?", [
        ("Rozkład normalny", False),
        ("Rozkład hipergeometryczny", False),
        ("Rozkład Poissona", True),
        ("Rozkład dwumianowy", False),
    ]),
    ("Jakie jest znaczenie wartości P < 0.05 w teście statystycznym?", [
        ("Wynik jest statystycznie istotny", True),
        ("Wynik jest statystycznie nieistotny", False),
        ("Prawdopodobieństwo błędu II rodzaju jest wysokie", False),
        ("Hipoteza zerowa jest prawdziwa", False),
    ]),
    ("Jakie są wymagania dotyczące próbki w teście chi-kwadrat?", [
        ("Próba musi być mała i jednorodna", False),
        ("Próba musi pochodzić z jednego regionu", False),
        ("Próba musi być wystarczająco duża i losowa", True),
        ("Próba musi mieć dokładnie 30 obserwacji", False),
    ]),
    ("Co zakłada hipoteza zerowa w teście statystycznym?", [
        ("Brak różnic lub efektu", True),
        ("Istnienie różnic lub efektu", False),
        ("Prawdziwość hipotezy alternatywnej", False),
        ("Prawdziwość rozkładu normalnego", False),
    ]),
    ("Jakie jest prawdopodobieństwo uzyskania orła w rzucie symetryczną monetą?", [
        ("0.25", False),
        ("0.75", False),
        ("0.50", True),
        ("1.00", False),
    ]),
    ("Które z poniższych jest przykładem danych kategorycznych?", [
        ("Wzrost w centymetrach", False),
        ("Kolor oczu", True),
        ("Czas reakcji w sekundach", False),
        ("Wynik testu na skali punktowej", False),
    ]),
    ("Jaki test statystyczny stosuje się do analizy dwóch zmiennych kategorycznych?", [
        ("Test chi-kwadrat", True),
        ("Test t Studenta", False),
        ("Test ANOVA", False),
        ("Test Kołmogorowa-Smirnowa", False),
    ]),
    ("Co oznacza hipoteza alternatywna w teście statystycznym?", [
        ("Brak różnic lub efektu", False),
        ("Istnienie różnic lub efektu", True),
        ("Prawdziwość hipotezy zerowej", False),
        ("Brak odchylenia standardowego", False),
    ]),
    ("Jakie jest prawdopodobieństwo wyrzucenia pary orzeł-orzeł (O,O) w pojedynczym rzucie dwoma monetami?", [
        ("0.25", True),
        ("0.50", False),
        ("0.75", False),
        ("1.00", False),
    ]),
    ("Jakie jest znaczenie mocy testu w kontekście skuteczności szczepionki?", [
        ("Moc testu określa prawdopodobieństwo odrzucenia hipotezy zerowej, gdy jest ona prawdziwa", False),
        ("Moc testu określa prawdopodobieństwo nie popełnienia błędu II rodzaju", True),
        ("Moc testu określa prawdopodobieństwo przyjęcia hipotezy zerowej, gdy jest ona fałszywa", False),
        ("Moc testu określa prawdopodobieństwo popełnienia błędu I rodzaju", False),
    ]),
    (
        "W eksperymencie rzucamy trzema niezależnymi monetami. "
        "Jakie jest prawdopodobieństwo wyrzucenia dokładnie jednego orła?",
        [
            ("0.125", False),
            ("0.375", True),
            ("0.500", False),
            ("0.625", False),
        ],
    ),
    ("W jakim celu stosuje się funkcję lm() w R?", [
        ("Do analizy korelacji", False),
        ("Do dopasowania modelu liniowego", True),
        ("Do obliczania średniej arytmetycznej", False),
        ("Do tworzenia histogramów", False),
    ]),
    ("Jaką funkcję w R należy użyć, aby obliczyć korelację między dwiema zmiennymi?", [
        ("lm()", False),
        ("mean()", False),
        ("cor()", True),
        ("sum()", False),
    ]),
    ("Która z poniższych funkcji w R jest używana do obliczania mediany?", [
        ("median()", True),
        ("mean()", False),
        ("mode()", False),
        ("sum()", False),
    ]),
    ("Jaką funkcję w R należy użyć, aby utworzyć wykres pudełkowy?", [
        ("hist()", False),
        ("barplot()", False),
        ("plot()", False),
        ("boxplot()", True),
    ]),
    ("Co oznacza termin \"próba losowa\" w statystyce?", [
        ("Próba wybrana celowo przez badacza", False),
        ("Próba wybrana w taki sposób, że każda jednostka ma równą szansę bycia wybraną", True),
        ("Próba wybrana na podstawie wcześniejszych badań", False),
        ("Próba wybrana ze względu na dostępność jednostek", False),
    ]),
    ("Jaki jest cel testu ANOVA?", [
        ("Do analizy korelacji między dwoma zmiennymi", False),
        ("Do porównania średnich więcej niż dwóch grup", True),
        ("Do obliczania wartości średniej", False),
        ("Do testowania hipotezy zerowej", False),
    ]),
    ("Który z poniższych jest testem nieparametrycznym?", [
        ("Test t Studenta", False),
        ("Test ANOVA", False),
        ("Test Kruskala-Wallisa", True),
        ("Test chi-kwadrat", False),
    ]),
    ("W jakiej sytuacji stosuje się test Wilcoxona?", [
        ("Gdy dane są normalnie rozłożone", False),
        ("Gdy dane nie są normalnie rozłożone", True),
        ("Gdy liczba próbek jest bardzo duża", False),
        ("Gdy dane są kategoryczne", False),
    ]),
    ("Co to jest przedział ufności?", [
        (
            "Zakres wartości, w którym z określonym prawdopodobieństwem znajduje się "
            "prawdziwa wartość parametru populacji",
            True,
        ),
        ("Zakres wartości, który jest zawsze symetryczny wokół średniej", False),
        ("Zakres wartości, który jest mniejszy od odchylenia standardowego", False),
        ("Zakres wartości, który obejmuje 50% próby", False),
    ]),
    ("Co oznacza odchylenie standardowe?", [
        ("Średnia wartość próby", False),
        ("Miara rozproszenia danych wokół średniej", True),
        ("Mediana danych", False),
        ("Maksymalna wartość w próbie", False),
    ]),
    ("Jakie jest prawdopodobieństwo wyrzucenia liczby 6 w pojedynczym rzucie sześcienną kostką do gry?", [
        ("0.10", False),
        ("0.20", False),
        ("0.1667", True),
        ("0.25", False),
    ]),
    ("Która funkcja w R jest używana do obliczania odchylenia standardowego?", [
        ("sd()", True),
        ("var()", False),
        ("mean()", False),
        ("summary()", False),
    ]),
    ("Jakie jest prawdopodobieństwo, że z talii 52 kart wyciągniesz kartę asa?", [
        ("0.10", False),
        ("0.12", False),
        ("0.077", True),
        ("0.15", False),
    ]),
    ("Co oznacza test dwustronny?", [
        (
            "Test, który sprawdza, czy średnia próbki jest różna od określonej wartości w obu kierunkach",
            True,
        ),
        ("Test, który sprawdza, czy średnia próbki jest mniejsza od określonej wartości", False),
        ("Test, który sprawdza, czy średnia próbki jest większa od określonej wartości", False),
        ("Test, który sprawdza tylko jedną stronę rozkładu", False),
    ]),
    ("Jakie jest prawdopodobieństwo wyrzucenia co najmniej jednego orła w dwóch rzutach monetą?", [
        ("0.75", True),
        ("0.50", False),
        ("0.25", False),
        ("0.20", False),
    ]),
    ("Która z poniższych metod jest używana do analizy zależności między dwiema zmiennymi liczbowymi?", [
        ("Test chi-kwadrat", False),
        ("Test ANOVA", False),
        ("Analiza regresji liniowej", True),
        ("Test Wilcoxona", False),
    ]),
    ("Co oznacza termin \"wartość oczekiwana\"?", [
        ("Mediana danych", False),
        ("Średnia ważona wszystkich możliwych wartości", True),
        ("Maksymalna wartość w próbie", False),
        ("Minimalna wartość w próbie", False),
    ]),
    ("Jaką funkcję w R należy użyć, aby utworzyć wykres punktowy?", [
        ("hist()", False),
        ("plot()", True),
        ("barplot()", False),
        ("boxplot()", False),
    ]),
    ("Co oznacza współczynnik korelacji Pearsona?", [
        ("Miara siły i kierunku liniowej zależności między dwiema zmiennymi", True),
        ("Miara centralnej tendencji w danych", False),
        ("Miara rozproszenia danych", False),
        ("Miara kategoryzacji danych", False),
    ]),
    ("Który z poniższych jest testem parametrycznym?", [
        ("Test t Studenta", True),
        ("Test Kruskala-Wallisa", False),
        ("Test Wilcoxona", False),
        ("Test Mann-Whitneya", False),
    ]),
    ("Co oznacza współczynnik determinacji R²?", [
        ("Miara centralnej tendencji", False),
        ("Miara, jak dobrze model dopasowuje się do danych", True),
        ("Miara rozproszenia danych", False),
        ("Miara liczby stopni swobody", False),
    ]),
]


def normalize_question(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = text.replace("ł", "l").replace("ą", "a").replace("ę", "e")
    text = text.replace("ó", "o").replace("ś", "s").replace("ć", "c")
    text = text.replace("ń", "n").replace("ź", "z").replace("ż", "z")
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_raw_item(item: tuple) -> tuple[str, list[tuple[str, bool]], str | None]:
    if len(item) == 3:
        q, answers, image = item
        return q, answers, image
    q, answers = item
    return q, answers, None


def dedupe(questions: list[tuple]) -> list[tuple]:
    seen: dict[str, tuple[str, list[tuple[str, bool]], str | None]] = {}
    for item in questions:
        q, answers, image = parse_raw_item(item)
        key = normalize_question(q)
        if key not in seen:
            seen[key] = (q, answers, image)
        elif len(answers) > len(seen[key][1]):
            seen[key] = (q, answers, image)
    return list(seen.values())


def to_quiz_json(questions: list[tuple]) -> list[dict]:
    out = []
    for q, answers, image in questions:
        entry = {
            "question": q.strip(),
            "answers": [{"text": a, "correct": c} for a, c in answers],
        }
        if image:
            entry["image"] = image
        out.append(entry)
    return out


def main() -> None:
    unique = dedupe(RAW)
    questions = to_quiz_json(unique)

    data = {
        "id": "peiar",
        "name": "Planowanie i Analiza Eksperymentu (PEIAR)",
        "description": "Pytania wielokrotnego wyboru z materiałów egzaminacyjnych. 1 pkt za poprawną odpowiedź.",
        "questions": questions,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    subjects = json.loads(SUBJECTS.read_text(encoding="utf-8"))
    for s in subjects:
        if s["id"] == "peiar":
            s["questionCount"] = len(questions)
    SUBJECTS.write_text(json.dumps(subjects, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Zapisano {len(questions)} unikalnych pytan (z {len(RAW)} wpisow zrodlowych)")


if __name__ == "__main__":
    main()
