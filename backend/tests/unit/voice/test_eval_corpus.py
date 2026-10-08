"""Corre tests/voice/commands.jsonl (Fase 13.6 "Afinacion", >= 150 frases
clinicas + >= 60 de recepcion, docs/06... C4) como parte de la suite normal
-- asi una regresion en nlu_fast.match la detecta `pytest`, no solo quien se
acuerde de correr `python -m app.voice.eval` a mano."""

import json
from pathlib import Path

import pytest

from app.voice import nlu_fast

_CORPUS_PATH = Path(__file__).parent.parent.parent / "voice" / "commands.jsonl"


def _load_corpus() -> list[dict[str, str]]:
    entries = []
    with _CORPUS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


_CORPUS = _load_corpus()


def test_corpus_has_the_minimum_required_phrases() -> None:
    clinica = [e for e in _CORPUS if e["role"] == "clinica"]
    recepcion = [e for e in _CORPUS if e["role"] == "recepcion"]
    assert len(clinica) >= 150
    assert len(recepcion) >= 60


@pytest.mark.parametrize("entry", _CORPUS, ids=[e["transcript"] for e in _CORPUS])
def test_fast_path_recognizes_the_expected_intent(entry: dict[str, str]) -> None:
    match = nlu_fast.match(entry["transcript"])
    actual = match.intent if match is not None else None
    assert actual == entry["expected_intent"]
