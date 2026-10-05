from datetime import date

from app.modules.patients.rules import build_full_name, calculate_age


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
