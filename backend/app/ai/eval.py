"""Mide la precision del intérprete contra tests/ai/corpus.jsonl usando el Ollama real
configurado en .env (docs/03_AGENTE_IA_VOZ.md sec. 10) -- a diferencia de las pruebas de
integracion, que usan un FakeOllama para no depender de red/modelo en CI.

Uso:
    python -m app.ai.eval
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.ai import dental_parser, ollama_client
from app.ai.actions import ACTION_MODELS_BY_TYPE, AiInterpretResult
from app.core.config import get_settings
from app.modules.diagnosis.rules import DIAGNOSIS_CODES
from app.modules.odontogram.finding_catalog import FINDING_CODES
from app.modules.records.rules import HISTORY_CATEGORIES

_CORPUS_PATH = Path(__file__).parent.parent.parent / "tests" / "ai" / "corpus.jsonl"
_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_es.md"

# Catalogo representativo para el eval (no depende de una BD/clinica real): coincide
# con el seed de procedure_catalog en app/seed.py.
_SAMPLE_PROCEDURE_CODES = (
    "consulta",
    "limpieza",
    "resina",
    "endodoncia_unirradicular",
    "corona",
)


def _system_prompt(transcript: str) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        finding_codes=", ".join(FINDING_CODES),
        procedure_codes=", ".join(_SAMPLE_PROCEDURE_CODES),
        diagnosis_codes=", ".join(DIAGNOSIS_CODES),
        history_categories=", ".join(HISTORY_CATEGORIES),
        patient_name="Paciente de prueba",
        screen="atencion",
        denticion="permanente",
        parser_hints=dental_parser.build_hints(transcript),
    )


def _load_corpus() -> list[dict[str, Any]]:
    entries = []
    with _CORPUS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _matches_expected(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    if actual.get("type") != expected.get("type"):
        return False
    for key in ("tooth_fdi", "diagnosis_code", "procedure_code", "section"):
        if key in expected and actual.get(key) != expected[key]:
            return False
    return "surfaces" not in expected or set(actual.get("surfaces") or []) == set(
        expected["surfaces"]
    )


async def _interpret_raw(transcript: str, model: str) -> list[dict[str, Any]]:
    response = await ollama_client.chat(
        model=model,
        system_prompt=_system_prompt(transcript),
        user_prompt=transcript,
        json_schema=AiInterpretResult.model_json_schema(),
    )
    content = response.get("message", {}).get("content", "{}")
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        return []
    actions = raw.get("actions", [])
    return [a for a in actions if isinstance(a, dict) and a.get("type") in ACTION_MODELS_BY_TYPE]


async def run_eval() -> None:
    settings = get_settings()
    corpus = _load_corpus()

    per_type_correct: dict[str, int] = {}
    per_type_total: dict[str, int] = {}
    tooth_correct = 0
    tooth_total = 0
    surface_correct = 0
    surface_total = 0

    for entry in corpus:
        transcript = entry["transcript"]
        expected_actions: list[dict[str, Any]] = entry["expected"]
        actual_actions = await _interpret_raw(transcript, settings.ollama_model)

        for expected in expected_actions:
            action_type = expected["type"]
            per_type_total[action_type] = per_type_total.get(action_type, 0) + 1
            match = next((a for a in actual_actions if _matches_expected(a, expected)), None)
            if match is not None:
                per_type_correct[action_type] = per_type_correct.get(action_type, 0) + 1

            if "tooth_fdi" in expected:
                tooth_total += 1
                if match is not None:
                    tooth_correct += 1
            if "surfaces" in expected:
                surface_total += 1
                if match is not None:
                    surface_correct += 1

    print(f"Modelo evaluado: {settings.ollama_model}")
    print(f"Dictados en el corpus: {len(corpus)}\n")
    print("Precision por tipo de accion:")
    for action_type in sorted(per_type_total):
        correct = per_type_correct.get(action_type, 0)
        total = per_type_total[action_type]
        print(f"  {action_type}: {correct}/{total} ({100 * correct / total:.0f}%)")

    if tooth_total:
        tooth_pct = 100 * tooth_correct / tooth_total
        print(f"\nPiezas FDI correctas: {tooth_correct}/{tooth_total} ({tooth_pct:.0f}%)")
    if surface_total:
        surface_pct = 100 * surface_correct / surface_total
        print(f"Superficies correctas: {surface_correct}/{surface_total} ({surface_pct:.0f}%)")


if __name__ == "__main__":
    asyncio.run(run_eval())
