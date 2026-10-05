from app.modules.documents.rules import SIGNER_RELATIONSHIPS, TEMPLATE_CODES, render_template


def test_template_catalog_has_expected_defaults() -> None:
    assert set(TEMPLATE_CODES) == {"general", "extraccion", "endodoncia", "anestesia"}


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
