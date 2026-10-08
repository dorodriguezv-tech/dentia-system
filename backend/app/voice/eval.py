"""Mide la precision de la ruta rapida (nlu_fast, sin LLM) contra
tests/voice/commands.jsonl -- Fase 13.6 "Afinacion" (docs/06_INSTRUCCIONES...
sec. C4): el criterio de aceptacion de esa etapa es "intencion correcta >= 90%
en la ruta rapida". A diferencia de `app/ai/eval.py` (mide el intérprete LLM
contra Ollama real), esto es texto puro -- no necesita Ollama ni base de
datos, por eso no es async.

Uso:
    python -m app.voice.eval
"""

import json
from pathlib import Path

from app.voice import nlu_fast

_CORPUS_PATH = Path(__file__).parent.parent.parent / "tests" / "voice" / "commands.jsonl"
_ACCEPTANCE_PCT = 90.0


def _load_corpus() -> list[dict[str, str]]:
    entries = []
    with _CORPUS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def run_eval() -> None:
    corpus = _load_corpus()

    per_role_correct: dict[str, int] = {}
    per_role_total: dict[str, int] = {}
    per_intent_correct: dict[str, int] = {}
    per_intent_total: dict[str, int] = {}
    failures: list[tuple[str, str, str | None]] = []

    for entry in corpus:
        transcript = entry["transcript"]
        role = entry["role"]
        expected_intent = entry["expected_intent"]

        match = nlu_fast.match(transcript)
        actual_intent = match.intent if match is not None else None
        is_correct = actual_intent == expected_intent

        per_role_total[role] = per_role_total.get(role, 0) + 1
        per_intent_total[expected_intent] = per_intent_total.get(expected_intent, 0) + 1
        if is_correct:
            per_role_correct[role] = per_role_correct.get(role, 0) + 1
            per_intent_correct[expected_intent] = per_intent_correct.get(expected_intent, 0) + 1
        else:
            failures.append((transcript, expected_intent, actual_intent))

    total = len(corpus)
    total_correct = sum(per_role_correct.values())

    print(f"Frases en el corpus: {total}\n")
    print("Precision por rol:")
    for role in sorted(per_role_total):
        correct = per_role_correct.get(role, 0)
        role_total = per_role_total[role]
        print(f"  {role}: {correct}/{role_total} ({100 * correct / role_total:.0f}%)")

    print("\nPrecision por intencion:")
    for intent in sorted(per_intent_total):
        correct = per_intent_correct.get(intent, 0)
        intent_total = per_intent_total[intent]
        marker = "" if correct == intent_total else "  <-- revisar"
        print(f"  {intent}: {correct}/{intent_total} ({100 * correct / intent_total:.0f}%){marker}")

    overall_pct = 100 * total_correct / total if total else 0.0
    cumple = "CUMPLE" if overall_pct >= _ACCEPTANCE_PCT else "NO CUMPLE"
    print(f"\nTotal: {total_correct}/{total} ({overall_pct:.1f}%)")
    print(f"Criterio de aceptacion (doc 06, 13.6): >= {_ACCEPTANCE_PCT:.0f}% -> {cumple}")

    if failures:
        print(f"\nFallos ({len(failures)}):")
        for transcript, expected, actual in failures:
            print(f"  {transcript!r}: esperado {expected!r}, obtuvo {actual!r}")


if __name__ == "__main__":
    run_eval()
