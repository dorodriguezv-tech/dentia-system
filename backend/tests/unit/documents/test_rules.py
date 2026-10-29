from app.modules.documents.rules import (
    LEGACY_EXAMPLE_TEMPLATE_CODES,
    SIGNER_RELATIONSHIPS,
    TEMPLATE_CATEGORIES,
    TEMPLATE_CATEGORY_LABELS,
    TEMPLATE_CODES,
    TEMPLATE_EXTRA_FIELDS,
    render_template,
)


def test_template_catalog_has_24_official_formats() -> None:
    # Los 24 formatos oficiales de docs/formatos (26 PDF originales, 2
    # duplicados exactos descartados -- ver plan aprobado).
    assert len(TEMPLATE_CODES) == 24
    assert len(set(TEMPLATE_CODES)) == 24


def test_template_categories_cover_every_code_with_a_known_category() -> None:
    assert set(TEMPLATE_CATEGORIES.keys()) == set(TEMPLATE_CODES)
    assert set(TEMPLATE_CATEGORIES.values()) <= set(TEMPLATE_CATEGORY_LABELS.keys())


def test_pediatric_codes_all_end_with_pediatrico_suffix() -> None:
    pediatric_codes = [c for c in TEMPLATE_CODES if "pediatrico" in c]
    assert len(pediatric_codes) == 8
    assert all(c.endswith("_pediatrico") for c in pediatric_codes)


def test_extra_fields_only_declared_for_known_codes() -> None:
    assert set(TEMPLATE_EXTRA_FIELDS.keys()) <= set(TEMPLATE_CODES)


def test_extra_fields_keys_are_unique_within_each_template() -> None:
    for code, specs in TEMPLATE_EXTRA_FIELDS.items():
        keys = [spec.key for spec in specs]
        assert len(keys) == len(set(keys)), f"claves repetidas en {code}"


def test_legacy_example_codes_no_longer_in_catalog_except_endodoncia() -> None:
    # "endodoncia" es ambos: codigo de ejemplo viejo y codigo real nuevo (ver
    # docstring de rules.LEGACY_EXAMPLE_TEMPLATE_CODES) -- los otros 3 ya no
    # existen como formato real, solo quedan retirados en la BD.
    assert set(LEGACY_EXAMPLE_TEMPLATE_CODES) - set(TEMPLATE_CODES) == {
        "general",
        "extraccion",
        "anestesia",
    }
    assert "endodoncia" in TEMPLATE_CODES


def test_signer_relationships_catalog() -> None:
    assert set(SIGNER_RELATIONSHIPS) == {"paciente", "tutor", "otro"}


def test_render_simple_variable() -> None:
    assert render_template("Hola {{nombre}}", {"nombre": "Jose"}) == "Hola Jose"


def test_render_nested_variable() -> None:
    html = "Paciente: {{paciente.nombre}}, edad {{paciente.edad}}"
    result = render_template(html, {"paciente": {"nombre": "Ana", "edad": 30}})
    assert result == "Paciente: Ana, edad 30"


def test_render_missing_variable_becomes_empty() -> None:
    assert render_template("Valor: {{no.existe}}", {}) == "Valor: "


def test_render_escapes_html_special_characters() -> None:
    result = render_template("{{nombre}}", {"nombre": "<script>alert(1)</script>"})
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

    result_amp = render_template("{{nombre}}", {"nombre": "Juan & Maria"})
    assert result_amp == "Juan &amp; Maria"


def test_render_multiple_variables() -> None:
    html = "{{a}} y {{b}}"
    assert render_template(html, {"a": "uno", "b": "dos"}) == "uno y dos"


def test_render_leaves_unknown_tokens_patterns_untouched_when_not_matching() -> None:
    assert render_template("{sin llaves dobles}", {}) == "{sin llaves dobles}"
