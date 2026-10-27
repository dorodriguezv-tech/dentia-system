from datetime import date

from app.modules.patients.rules import build_full_name, calculate_age, calculate_patient_type


def test_calculate_age_before_birthday_this_year() -> None:
    assert calculate_age(date(2000, 6, 15), as_of=date(2026, 6, 14)) == 25


def test_calculate_age_on_birthday() -> None:
    assert calculate_age(date(2000, 6, 15), as_of=date(2026, 6, 15)) == 26


def test_calculate_age_after_birthday() -> None:
    assert calculate_age(date(2000, 6, 15), as_of=date(2026, 7, 1)) == 26


def test_build_full_name_with_both_last_names() -> None:
    assert build_full_name("Maria", "Lopez", "Garcia") == "Maria Lopez Garcia"


def test_build_full_name_without_maternal_last_name() -> None:
    assert build_full_name("Maria", "Lopez", None) == "Maria Lopez"


def test_build_full_name_without_maternal_last_name_empty_string() -> None:
    assert build_full_name("Maria", "Lopez", "") == "Maria Lopez"


def test_calculate_patient_type_under_cutoff_is_pediatric() -> None:
    # 11 anios al corte -> pediatrico (cutoff = 12, ver PEDIATRIC_AGE_CUTOFF_YEARS)
    assert calculate_patient_type(date(2015, 1, 1), as_of=date(2026, 1, 1)) == "pediatrico"


def test_calculate_patient_type_exactly_at_cutoff_is_adult() -> None:
    # Cumple 12 anios justo en as_of -> adulto (el corte es inclusivo hacia adulto)
    assert calculate_patient_type(date(2014, 1, 1), as_of=date(2026, 1, 1)) == "adulto"


def test_calculate_patient_type_adult() -> None:
    assert calculate_patient_type(date(1990, 5, 20), as_of=date(2026, 1, 1)) == "adulto"
