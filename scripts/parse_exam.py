#!/usr/bin/env python3
"""Parse clean exam text (■/□ format) into docs/data/ssi.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "docs" / "data" / "exam_clean.txt"
DEFAULT_OUT = ROOT / "docs" / "data" / "ssi.json"


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*→\s*", " → ", text)
    return text


def parse_exam(raw: str) -> list[dict]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    # Skip header before first numbered question
    start = re.search(r"^1\)\s", raw, re.MULTILINE)
    if start:
        raw = raw[start.start() :]

    blocks = re.split(r"\n(?=\d+\)\s)", raw.strip())
    questions: list[dict] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [ln.rstrip() for ln in block.split("\n")]
        m = re.match(r"^(\d+)\)\s*(.*)$", lines[0])
        if not m:
            continue
        q_num = int(m.group(1))
        question_parts = [m.group(2).strip()] if m.group(2).strip() else []
        answers: list[dict] = []

        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped[0] in "■□":
                correct = stripped[0] == "■"
                answers.append({"text": stripped[1:].strip(), "correct": correct})
            elif answers and not re.match(r"^\d+\)\s", stripped):
                # Wrapped answer or question continuation
                if re.match(r"^[a-ząćęłńóśźż]{1,4}$", stripped, re.I) and len(stripped) <= 4:
                    # Skip PDF garbage fragments (e.g. broken formula lines)
                    continue
                if answers:
                    answers[-1]["text"] += " " + stripped
                else:
                    question_parts.append(stripped)
            elif not answers:
                question_parts.append(stripped)

        question = normalize_text(" ".join(question_parts))
        for a in answers:
            a["text"] = normalize_text(a["text"])

        if not question or not answers:
            print(f"Warning: skipping malformed block #{q_num}", file=sys.stderr)
            continue
        questions.append({"question": question, "answers": answers})

    return questions


def main() -> None:
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    raw = in_path.read_text(encoding="utf-8")
    questions = parse_exam(raw)

    data = {
        "id": "ssi",
        "name": "Systemy Sztucznej Inteligencji",
        "description": "Egzamin — 256 pytań wielokrotnego wyboru. 1 pkt za wszystkie poprawne odpowiedzi.",
        "questions": questions,
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed {len(questions)} questions → {out_path}")


if __name__ == "__main__":
    main()
