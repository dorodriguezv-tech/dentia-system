"""C3 del doc 06, sec. 3 del diseno: "pulpitis reversibe" -> "pulpitis
reversible" es el ejemplo literal que se usa ahi para justificar esta
correccion -- es la primera prueba de abajo."""

from app.ai.vocab.correct import correct_transcript

_VOCAB = (
    "pulpitis reversible",
    "gingivitis",
    "endodoncia",
    "necrosis pulpar",
    "caries recurrente",
)


def test_corrects_a_two_word_catalog_phrase() -> None:
    text = "el paciente tiene pulpitis reversibe en la pieza 36"
    assert (
        correct_transcript(text, _VOCAB) == "el paciente tiene pulpitis reversible en la pieza 36"
    )


def test_corrects_a_single_word_with_a_small_typo() -> None:
    assert correct_transcript("tiene gingivits leve", _VOCAB) == "tiene gingivitis leve"


def test_leaves_common_spanish_words_untouched() -> None:
    text = "buenos dias doctor como esta usted"
    assert correct_transcript(text, _VOCAB) == text


def test_leaves_an_exact_vocabulary_word_untouched() -> None:
    text = "requiere endodoncia en la pieza 36"
    assert correct_transcript(text, _VOCAB) == text


def test_preserves_leading_capitalization() -> None:
    text = "Pulpitis Reversibe en la pieza 36"
    assert correct_transcript(text, _VOCAB) == "Pulpitis reversible en la pieza 36"


def test_does_not_correct_short_words_even_if_similar_by_chance() -> None:
    # "sana" (4 letras) nunca se intenta corregir -- por debajo del largo
    # minimo, sin importar que tan parecida sea a algun termino del
    # vocabulario.
    assert correct_transcript("la pieza esta sana", ("sano",)) == "la pieza esta sana"


def test_empty_text_returns_empty_text() -> None:
    assert correct_transcript("", _VOCAB) == ""


def test_empty_vocabulary_returns_the_original_text() -> None:
    text = "tiene gingivits leve"
    assert correct_transcript(text, ()) == text


def test_an_exact_word_right_before_a_real_next_word_does_not_swallow_it() -> None:
    """Bug real: "endodoncia en" calzaba por pura casualidad contra
    "endodoncia" sola (termino de una palabra) y se tragaba el "en"."""
    text = "requiere endodoncia en la pieza 36"
    assert correct_transcript(text, _VOCAB) == text


def test_corrects_a_phrase_even_when_its_first_word_is_also_a_standalone_term() -> None:
    """ "caries" es por si sola un termino valido (del diccionario externo) Y
    el principio de la frase "caries recurrente" (catalogo de diagnosticos)
    -- debe seguir reconociendo la frase completa."""
    vocab = (*_VOCAB, "caries")
    text = "caries recurente en la 46"
    assert correct_transcript(text, vocab) == "caries recurrente en la 46"
