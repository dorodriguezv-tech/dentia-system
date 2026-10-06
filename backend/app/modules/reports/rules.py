"""Reglas de calculo del modulo reports (CLAUDE.md Fase 11), aisladas de la BD.

El modulo `reports` no agrega tablas nuevas (docs/02 sec. 2: "vistas/consultas de
solo lectura"): cada reporte se arma en `service.py` a partir de modelos de otros
modulos ya existentes. Aqui solo viven los calculos puros (tasas, acumulados por
grupo) para poder probarlos sin base de datos.
"""

from collections.abc import Hashable
from decimal import ROUND_HALF_UP, Decimal
from typing import TypeVar

K = TypeVar("K", bound=Hashable)

# Un estado REPROGRAMADA no es un resultado real de la cita original (la cita se
# "convierte" en una nueva, ver agenda/rules.py) -- se excluye del denominador de la
# tasa de no-show para no inflarla artificialmente con citas que en realidad si se
# atendieron, solo que en otro horario.
_EXCLUDED_FROM_NO_SHOW_RATE = ("REPROGRAMADA",)


def no_show_rate(counts_by_status: dict[str, int]) -> Decimal:
    """Porcentaje de citas que terminaron en NO_SHOW sobre el total de citas con un
    resultado real (excluye REPROGRAMADA). Devuelve 0.00 si no hay citas con resultado."""
    denominator = sum(
        count
        for status, count in counts_by_status.items()
        if status not in _EXCLUDED_FROM_NO_SHOW_RATE
    )
    if denominator <= 0:
        return Decimal("0.00")
    no_show = counts_by_status.get("NO_SHOW", 0)
    rate = (Decimal(no_show) / Decimal(denominator)) * Decimal("100")
    return rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Catalogo configurable (CLAUDE.md sec. 7): que estados de TreatmentPlan cuentan como
# "pendiente" para el resumen del tablero -- ver docs/PENDIENTES_CLINICOS.md.
PENDING_PLAN_STATUSES = ("BORRADOR", "PRESENTADO")
ACCEPTED_PLAN_STATUSES = ("ACEPTADO",)


def sum_amounts_by_key(rows: list[tuple[K, Decimal]]) -> dict[K, Decimal]:
    """Acumula `amount` por una llave de agrupacion (p.ej. id de profesional),
    preservando el orden de primera aparicion. Sembrar en Decimal('0.00') y no en
    Decimal('0') es obligatorio: un Numeric(10,2) que llega en cero desde la base
    serializa a JSON como "0.00", y Decimal('0') (sin escala explicita) serializa
    como "0" -- un acumulador sembrado distinto rompe la consistencia del formato."""
    totals: dict[K, Decimal] = {}
    for key, amount in rows:
        totals[key] = totals.get(key, Decimal("0.00")) + amount
    return totals
