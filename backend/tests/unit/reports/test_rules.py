from datetime import date
from decimal import Decimal

from app.modules.reports.rules import no_show_rate, sum_amounts_by_key
from app.modules.reports.service import resolve_date_range


def test_no_show_rate_with_no_appointments() -> None:
    assert no_show_rate({}) == Decimal("0.00")


def test_no_show_rate_excludes_reprogramada_from_denominator() -> None:
    counts = {"TERMINADA": 6, "NO_SHOW": 2, "REPROGRAMADA": 10}
    # 2 / (6 + 2) = 25.00%, no 2 / 18 -- las reprogramadas no cuentan como resultado.
    assert no_show_rate(counts) == Decimal("25.00")


def test_no_show_rate_rounds_to_two_decimals() -> None:
    counts = {"TERMINADA": 2, "NO_SHOW": 1}
    assert no_show_rate(counts) == Decimal("33.33")


def test_no_show_rate_all_no_show() -> None:
    assert no_show_rate({"NO_SHOW": 3}) == Decimal("100.00")


def test_sum_amounts_by_key_seeds_with_two_decimal_zero() -> None:
    totals = sum_amounts_by_key([])
    assert totals == {}


def test_sum_amounts_by_key_accumulates_per_group() -> None:
    rows = [("a", Decimal("100.00")), ("b", Decimal("50.00")), ("a", Decimal("25.50"))]
    totals = sum_amounts_by_key(rows)
    assert totals == {"a": Decimal("125.50"), "b": Decimal("50.00")}
    # Decimal("0") (sin escala) serializa a JSON como "0" en vez de "0.00" -- el
    # acumulador debe arrancar sembrado con dos decimales (ver docs/02 sec. 5.10).
    assert str(totals["b"]) == "50.00"


def test_resolve_date_range_defaults_to_last_30_days() -> None:
    today = date(2026, 10, 15)
    date_from, date_to = resolve_date_range(None, None, today=today)
    assert date_to == today
    assert date_from == date(2026, 9, 15)


def test_resolve_date_range_keeps_explicit_values() -> None:
    date_from, date_to = resolve_date_range(
        date(2026, 1, 1), date(2026, 1, 31), today=date(2026, 10, 15)
    )
    assert (date_from, date_to) == (date(2026, 1, 1), date(2026, 1, 31))


def test_resolve_date_range_fills_only_missing_end() -> None:
    today = date(2026, 10, 15)
    date_from, date_to = resolve_date_range(date(2026, 10, 1), None, today=today)
    assert (date_from, date_to) == (date(2026, 10, 1), today)
