import numpy as np

from app.voice import wake


def test_is_wake_phrase_accepts_the_literal_word() -> None:
    assert wake.is_wake_phrase("Dentia, abre el expediente de Juan Pérez")


def test_is_wake_phrase_is_case_and_accent_insensitive() -> None:
    assert wake.is_wake_phrase("DENTÍA abre la agenda")
    assert wake.is_wake_phrase("dentia abre la agenda")


def test_is_wake_phrase_rejects_similar_words() -> None:
    # "dentista"/"de tia" no deben despertar a Dentia (sec. 5 del diseno).
    assert not wake.is_wake_phrase("dentista, tengo una pregunta")
    assert not wake.is_wake_phrase("de tia ya sabes lo que te dije")


def test_is_wake_phrase_rejects_when_dentia_is_not_the_first_word() -> None:
    assert not wake.is_wake_phrase("oye dentia abre el expediente")


def test_is_wake_phrase_rejects_empty_transcript() -> None:
    assert not wake.is_wake_phrase("")
    assert not wake.is_wake_phrase("   ")


def test_pcm16_to_float32_normalizes_range() -> None:
    pcm = np.array([0, 16384, -16384, 32767, -32768], dtype="<i2").tobytes()
    audio = wake.pcm16_to_float32(pcm)
    assert audio.dtype == np.float32
    assert audio[0] == 0
    assert 0.49 < audio[1] < 0.51
    assert -0.51 < audio[2] < -0.49


def test_has_speech_detects_silence_vs_tone() -> None:
    silence = np.zeros(16_000, dtype=np.float32)
    assert not wake.has_speech(silence)

    tone = (0.5 * np.sin(np.linspace(0, 100, 16_000))).astype(np.float32)
    assert wake.has_speech(tone)


def test_has_speech_handles_empty_array() -> None:
    assert not wake.has_speech(np.array([], dtype=np.float32))
