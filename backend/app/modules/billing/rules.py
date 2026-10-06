"""Reglas y catalogos de cobranza (CLAUDE.md Fase 10; regla 4: un presupuesto aceptado
no es un pago, y un pago no cambia el estado clinico), aisladas de la BD."""

from decimal import Decimal

PAYMENT_METHODS: tuple[str, ...] = ("efectivo", "tarjeta", "transferencia")

# El estado de un Charge no se guarda: se calcula a partir de lo que de verdad se le ha
# aplicado (regla 4 -- la "verdad" vive en los pagos aplicados, no en una bandera que
# alguien pueda olvidar actualizar). CANCELADO es la unica excepcion real (is_active).
CHARGE_STATUSES: tuple[str, ...] = ("PENDIENTE", "PARCIAL", "PAGADO", "CANCELADO")

CASH_SESSION_STATUSES: tuple[str, ...] = ("ABIERTA", "CERRADA")


def charge_balance(amount: Decimal, applied: Decimal) -> Decimal:
    return amount - applied


def charge_computed_status(*, is_active: bool, amount: Decimal, applied: Decimal) -> str:
    if not is_active:
        return "CANCELADO"
    if applied <= 0:
        return "PENDIENTE"
    if applied >= amount:
        return "PAGADO"
    return "PARCIAL"
