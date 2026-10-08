from datetime import date, time

from app.voice import datetime_parse


def test_extract_relative_date_hoy() -> None:
    assert datetime_parse.extract_relative_date("hoy", today=date(2026, 3, 5)) == date(2026, 3, 5)


def test_extract_relative_date_manana() -> None:
    assert datetime_parse.extract_relative_date("mañana", today=date(2026, 3, 5)) == date(
        2026, 3, 6
    )


def test_extract_relative_date_weekday_later_this_week() -> None:
    # 2026-03-05 es jueves (weekday()==3); "el viernes" es al dia siguiente.
    assert datetime_parse.extract_relative_date("el viernes", today=date(2026, 3, 5)) == date(
        2026, 3, 6
    )


def test_extract_relative_date_weekday_today_is_that_day() -> None:
    assert datetime_parse.extract_relative_date("el jueves", today=date(2026, 3, 5)) == date(
        2026, 3, 5
    )


def test_extract_relative_date_weekday_wraps_to_next_week() -> None:
    # "el lunes" dicho un jueves: el proximo lunes, no el de esta semana ya pasado.
    assert datetime_parse.extract_relative_date("el lunes", today=date(2026, 3, 5)) == date(
        2026, 3, 9
    )


def test_extract_relative_date_en_n_dias() -> None:
    assert datetime_parse.extract_relative_date("en 15 dias", today=date(2026, 3, 5)) == date(
        2026, 3, 20
    )


def test_extract_relative_date_unrecognized_returns_none() -> None:
    assert datetime_parse.extract_relative_date("el 21 de octubre", today=date(2026, 3, 5)) is None
    assert datetime_parse.extract_relative_date("", today=date(2026, 3, 5)) is None


def test_extract_time_of_day_numeric() -> None:
    assert datetime_parse.extract_time_of_day("a las 10") == time(10, 0)
    assert datetime_parse.extract_time_of_day("a las 10:30") == time(10, 30)
    assert datetime_parse.extract_time_of_day("a las 10 30") == time(10, 30)


def test_extract_time_of_day_spoken() -> None:
    assert datetime_parse.extract_time_of_day("a las diez") == time(10, 0)
    assert datetime_parse.extract_time_of_day("a las diez y media") == time(10, 30)


def test_extract_time_of_day_unrecognized_returns_none() -> None:
    assert datetime_parse.extract_time_of_day("por la tarde") is None
    assert datetime_parse.extract_time_of_day("") is None


def test_extract_time_of_day_rejects_out_of_range_hour() -> None:
    assert datetime_parse.extract_time_of_day("a las 99") is None


def test_format_date_es() -> None:
    assert datetime_parse.format_date_es(date(2026, 3, 5)) == "jueves 5 de marzo"
    assert datetime_parse.format_date_es(date(2026, 1, 1)) == "jueves 1 de enero"
