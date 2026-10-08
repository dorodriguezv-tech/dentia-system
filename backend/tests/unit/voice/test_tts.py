from pathlib import Path

import pytest

from app.voice import tts


class _FakeSettings:
    def __init__(
        self,
        *,
        voice_fake_mode: bool = False,
        voice_tts_engine: str = "piper",
        voice_tts_model_path: str = "",
    ) -> None:
        self.voice_fake_mode = voice_fake_mode
        self.voice_tts_engine = voice_tts_engine
        self.voice_tts_model_path = voice_tts_model_path


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    tts._phrase_cache.clear()


async def test_returns_none_in_fake_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts, "get_settings", lambda: _FakeSettings(voice_fake_mode=True))
    assert await tts.synthesize("Hola") is None


async def test_returns_none_when_engine_is_not_piper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts, "get_settings", lambda: _FakeSettings(voice_tts_engine="browser"))
    assert await tts.synthesize("Hola") is None


async def test_returns_none_when_model_path_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts, "get_settings", lambda: _FakeSettings(voice_tts_model_path=""))
    assert await tts.synthesize("Hola") is None


async def test_returns_none_when_model_file_does_not_exist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "no_existe.onnx"
    monkeypatch.setattr(
        tts, "get_settings", lambda: _FakeSettings(voice_tts_model_path=str(missing))
    )
    assert await tts.synthesize("Hola") is None


async def test_pcm_to_wav_builds_a_valid_header() -> None:
    pcm = b"\x01\x02\x03\x04"
    wav = tts._pcm_to_wav(pcm, sample_rate=22050)

    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "
    assert wav[36:40] == b"data"
    assert wav.endswith(pcm)


async def test_uses_the_phrase_cache_without_touching_settings_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _tracked_settings() -> _FakeSettings:
        calls["count"] += 1
        return _FakeSettings()

    tts._phrase_cache["¿Sí?"] = b"cached-wav-bytes"
    monkeypatch.setattr(tts, "get_settings", _tracked_settings)

    result = await tts.synthesize("¿Sí?")

    assert result == b"cached-wav-bytes"
    # Solo se consulta voice_fake_mode antes de revisar la cache -- 1 llamada.
    assert calls["count"] == 1


async def test_model_paths_requires_both_onnx_and_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model = tmp_path / "voz.onnx"
    model.write_bytes(b"fake-model")
    # Sin el .json junto al .onnx, _model_paths debe devolver None.
    monkeypatch.setattr(tts, "get_settings", lambda: _FakeSettings(voice_tts_model_path=str(model)))
    assert tts._model_paths() is None

    (tmp_path / "voz.onnx.json").write_text('{"audio": {"sample_rate": 22050}}')
    assert tts._model_paths() == (model, tmp_path / "voz.onnx.json")
