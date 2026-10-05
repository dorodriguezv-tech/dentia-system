from app.ai import dental_parser


class TestExtractToothMentions:
    def test_digit_form_with_trigger_word(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza 36 con caries") == [36]

    def test_digit_form_with_organo_dentario(self) -> None:
        assert dental_parser.extract_tooth_mentions("organo dentario 46 con resina") == [46]

    def test_digit_form_with_diente(self) -> None:
        assert dental_parser.extract_tooth_mentions("diente 11 fracturado") == [11]

    def test_compound_number_words_treinta_y_seis(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza treinta y seis caries oclusal") == [36]

    def test_compound_number_words_cuarenta_y_seis(self) -> None:
        assert dental_parser.extract_tooth_mentions("la cuarenta y seis tiene resina") == [46]

    def test_compound_number_words_ochenta_y_cinco(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza ochenta y cinco") == [85]

    def test_teen_word_dieciocho(self) -> None:
        assert dental_parser.extract_tooth_mentions("falta la dieciocho") == [18]

    def test_teen_word_once(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza once con caries") == [11]

    def test_twenty_word_veinticuatro(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza veinticuatro") == [24]

    def test_digit_pair_spoken_as_two_units_tres_seis(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza tres seis con pulpitis") == [36]

    def test_digit_pair_spoken_as_two_units_cuatro_ocho(self) -> None:
        assert dental_parser.extract_tooth_mentions("diente cuatro ocho") == [48]

    def test_article_el_with_digits(self) -> None:
        assert dental_parser.extract_tooth_mentions("el 65 tiene movilidad") == [65]

    def test_article_la_with_digits(self) -> None:
        assert dental_parser.extract_tooth_mentions("la 24 con sellador") == [24]

    def test_multiple_teeth_in_one_sentence(self) -> None:
        result = dental_parser.extract_tooth_mentions(
            "pieza treinta y seis caries, la cuarenta y seis con resina, falta la dieciocho"
        )
        assert result == [36, 46, 18]

    def test_invalid_tooth_number_is_not_returned(self) -> None:
        # 19 y 29 no son FDI validos (no existe posicion 9 en un cuadrante).
        assert dental_parser.extract_tooth_mentions("pieza diecinueve") == []
        assert dental_parser.extract_tooth_mentions("pieza veintinueve") == []

    def test_no_mention_returns_empty_list(self) -> None:
        assert dental_parser.extract_tooth_mentions("el paciente refiere dolor") == []

    def test_accents_are_ignored(self) -> None:
        assert dental_parser.extract_tooth_mentions("pérdida en la piéza treinta y seis") == [36]

    def test_temporary_tooth_is_detected(self) -> None:
        assert dental_parser.extract_tooth_mentions("pieza cincuenta y cinco") == [55]


class TestExtractSurfaces:
    def test_single_surface(self) -> None:
        assert dental_parser.extract_surfaces("caries oclusal") == ["O"]

    def test_two_surfaces_preserve_order(self) -> None:
        assert dental_parser.extract_surfaces("caries oclusal y distal") == ["O", "D"]

    def test_all_surface_words(self) -> None:
        text = "mesial distal vestibular bucal lingual palatino incisal"
        assert dental_parser.extract_surfaces(text) == ["M", "D", "V", "L", "P", "I"]

    def test_duplicate_words_deduplicated(self) -> None:
        assert dental_parser.extract_surfaces("oclusal y oclusal otra vez") == ["O"]

    def test_no_surface_words_returns_empty(self) -> None:
        assert dental_parser.extract_surfaces("sin hallazgos") == []


class TestNormalizeSurfaceWord:
    def test_known_word(self) -> None:
        assert dental_parser.normalize_surface_word("Oclusal") == "O"

    def test_bucal_maps_to_vestibular(self) -> None:
        assert dental_parser.normalize_surface_word("bucal") == "V"

    def test_unknown_word_returns_none(self) -> None:
        assert dental_parser.normalize_surface_word("xyz") is None


class TestBuildHints:
    def test_includes_teeth_and_surfaces(self) -> None:
        hints = dental_parser.build_hints("pieza treinta y seis caries oclusal y distal")
        assert "36" in hints
        assert "O" in hints and "D" in hints

    def test_no_hints_detected(self) -> None:
        assert dental_parser.build_hints("sin datos clinicos") == "sin pistas detectadas"
