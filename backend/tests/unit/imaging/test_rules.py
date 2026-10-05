from app.modules.imaging.rules import ALLOWED_CONTENT_TYPES, STUDY_TYPE_LABELS, STUDY_TYPES


def test_study_types_catalog_has_expected_defaults() -> None:
    assert set(STUDY_TYPES) == {
        "intraoral",
        "extraoral",
        "periapical",
        "bitewing",
        "panoramica",
        "cefalometria",
    }


def test_every_study_type_has_a_label() -> None:
    for code in STUDY_TYPES:
        assert STUDY_TYPE_LABELS[code]


def test_allowed_content_types_cover_jpg_png_pdf() -> None:
    assert set(ALLOWED_CONTENT_TYPES) == {"image/jpeg", "image/png", "application/pdf"}
