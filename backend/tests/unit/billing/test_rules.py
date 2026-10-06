from decimal import Decimal

from app.modules.billing.rules import charge_balance, charge_computed_status


def test_charge_balance_with_no_payments() -> None:
    assert charge_balance(Decimal("500"), Decimal("0")) == Decimal("500")


def test_charge_balance_with_partial_payment() -> None:
    assert charge_balance(Decimal("500"), Decimal("200")) == Decimal("300")


def test_charge_balance_fully_paid() -> None:
    assert charge_balance(Decimal("500"), Decimal("500")) == Decimal("0")


def test_computed_status_pendiente() -> None:
    status = charge_computed_status(is_active=True, amount=Decimal("500"), applied=Decimal("0"))
    assert status == "PENDIENTE"


def test_computed_status_parcial() -> None:
    status = charge_computed_status(is_active=True, amount=Decimal("500"), applied=Decimal("200"))
    assert status == "PARCIAL"


def test_computed_status_pagado() -> None:
    status = charge_computed_status(is_active=True, amount=Decimal("500"), applied=Decimal("500"))
    assert status == "PAGADO"


def test_computed_status_pagado_when_overpaid() -> None:
    status = charge_computed_status(is_active=True, amount=Decimal("500"), applied=Decimal("600"))
    assert status == "PAGADO"


def test_computed_status_cancelado_overrides_everything() -> None:
    status = charge_computed_status(is_active=False, amount=Decimal("500"), applied=Decimal("0"))
    assert status == "CANCELADO"
