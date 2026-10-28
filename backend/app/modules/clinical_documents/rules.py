"""Reglas y helpers puros de recetas/referencia/contrarreferencia, aislados de
la BD (igual criterio que documents/rules.py y records/rules.py: se prueban
sin fixtures)."""

from app.modules.records.rules import body_mass_index

MAX_MEDICATIONS_PER_PRESCRIPTION = 30


def next_folio(existing_count: int) -> str:
    """Folio consecutivo simple por clinica (decision documentada en
    clinical_documents/service.py::_next_prescription_folio): "RX-" + 6
    digitos con ceros a la izquierda, a partir de cuantas recetas existen ya
    en la clinica (anuladas incluidas, para que el folio nunca se repita)."""
    return f"RX-{existing_count + 1:06d}"


def allergy_summary(allergy_labels: list[str]) -> tuple[bool, str]:
    """ "Alergias: Si/No + cuales" (receta, docs/clinica) -- a partir de las
    alergias activas ya capturadas en el expediente (regla 8 de CLAUDE.md)."""
    if not allergy_labels:
        return False, ""
    return True, ", ".join(allergy_labels)


def vital_signs_summary_values(
    *,
    height_m: float | None,
    weight_kg: float | None,
    temperature: float | None,
    bp_systolic: int | None,
    bp_diastolic: int | None,
) -> dict[str, str]:
    """Formatea los campos de signos vitales que pide la receta/referencia
    (talla, peso, IMC, temperatura, tension arterial) con "-" como relleno
    cuando no hay dato -- nunca se bloquea la impresion por falta de un
    signo vital."""
    bmi = body_mass_index(height_m, weight_kg)
    tension = (
        f"{bp_systolic}/{bp_diastolic}"
        if bp_systolic is not None and bp_diastolic is not None
        else "-"
    )
    return {
        "talla": f"{height_m:.2f}" if height_m is not None else "-",
        "peso": f"{weight_kg:.1f}" if weight_kg is not None else "-",
        "imc": f"{bmi:.1f}" if bmi is not None else "-",
        "temperatura": f"{temperature:.1f}" if temperature is not None else "-",
        "tension": tension,
    }
