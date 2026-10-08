from app.ai.vocab import terms


def test_catalog_terms_includes_a_finding_label() -> None:
    assert "caries" in terms.catalog_terms()


def test_catalog_terms_includes_a_diagnosis_label_not_in_the_external_dictionary() -> None:
    # "pulpitis reversible" es el ejemplo del diseno (sec. 3 del doc 05) --
    # viene de app/modules/diagnosis/rules.py, no del PDF externo.
    assert "pulpitis reversible" in terms.catalog_terms()


def test_dictionary_terms_returns_an_empty_tuple_when_the_file_is_missing(monkeypatch) -> None:
    terms.dictionary_terms.cache_clear()
    monkeypatch.setattr(terms, "_TERMS_TXT", terms._TERMS_TXT.parent / "no_existe.txt")
    assert terms.dictionary_terms() == ()
    terms.dictionary_terms.cache_clear()


def test_dictionary_terms_reads_one_term_per_line(monkeypatch, tmp_path) -> None:
    terms.dictionary_terms.cache_clear()
    fake_file = tmp_path / "terminos_dentales.txt"
    fake_file.write_text("absceso\ncaries\n\n", encoding="utf-8")
    monkeypatch.setattr(terms, "_TERMS_TXT", fake_file)

    assert terms.dictionary_terms() == ("absceso", "caries")
    terms.dictionary_terms.cache_clear()


def test_combined_vocabulary_merges_both_sources_without_duplicates(monkeypatch, tmp_path) -> None:
    terms.dictionary_terms.cache_clear()
    terms.combined_vocabulary.cache_clear()
    fake_file = tmp_path / "terminos_dentales.txt"
    fake_file.write_text("caries\nabfraccion\n", encoding="utf-8")
    monkeypatch.setattr(terms, "_TERMS_TXT", fake_file)

    combined = terms.combined_vocabulary()

    assert "abfraccion" in combined
    assert "pulpitis reversible" in combined
    assert len(combined) == len(set(combined))
    terms.dictionary_terms.cache_clear()
    terms.combined_vocabulary.cache_clear()
