"""`app/ai/stt.py` carga un WhisperModel real -- estas pruebas mockean
`get_model()` (igual que el resto del proyecto mockea Ollama) para probar el
pegamento con hotwords/correccion (C3 del doc 06) sin un modelo real."""

from dataclasses import dataclass

from app.ai import stt


@dataclass
class _FakeSegment:
    text: str


class _FakeModel:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict] = []

    def transcribe(self, _audio, **kwargs):
        self.calls.append(kwargs)
        return [_FakeSegment(self._text)], None


def test_transcribe_pcm16_passes_hotwords_from_the_combined_vocabulary(monkeypatch) -> None:
    fake_model = _FakeModel("algo")
    monkeypatch.setattr(stt, "get_model", lambda: fake_model)
    monkeypatch.setattr(stt.vocab_terms, "combined_vocabulary", lambda: ("caries", "gingivitis"))

    stt.transcribe_pcm16(__import__("numpy").zeros(1600, dtype="float32"))

    assert len(fake_model.calls) == 1
    hotwords = fake_model.calls[0]["hotwords"]
    assert "caries" in hotwords
    assert "gingivitis" in hotwords


def test_transcribe_pcm16_corrects_the_transcribed_text(monkeypatch) -> None:
    fake_model = _FakeModel("tiene gingivits leve")
    monkeypatch.setattr(stt, "get_model", lambda: fake_model)
    monkeypatch.setattr(stt.vocab_terms, "combined_vocabulary", lambda: ("gingivitis",))

    result = stt.transcribe_pcm16(__import__("numpy").zeros(1600, dtype="float32"))

    assert result == "tiene gingivitis leve"


def test_transcribe_corrects_the_transcribed_text(monkeypatch) -> None:
    fake_model = _FakeModel("pulpitis reversibe")
    monkeypatch.setattr(stt, "get_model", lambda: fake_model)
    monkeypatch.setattr(stt.vocab_terms, "combined_vocabulary", lambda: ("pulpitis reversible",))

    result = stt.transcribe(b"fake-audio-bytes")

    assert result == "pulpitis reversible"
