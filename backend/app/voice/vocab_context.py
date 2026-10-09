"""Vocabulario de Whisper por CONTEXTO (resto de C3, pendiente #47 de
docs/PENDIENTES_CLINICOS.md): el vocabulario fijo (diccionario + catalogos
clinicos fijos, `app/ai/vocab/terms.py`) no puede traer los catalogos
ADMINISTRABLES de cada sucursal (B1 -- tipos de cita, hallazgos, diagnosticos,
categorias de antecedentes, palabras clave de alerta) ni los nombres de los
pacientes de esa clinica, porque ninguno de los dos existe hasta que la
clinica los da de alta. Esta funcion arma esos terminos en cada orden,
aparte del vocabulario fijo (que sigue siendo el `hotwords` de siempre,
sin cambios) -- se suman como `extra_hotwords` en `app/ai/stt.py`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agenda import service as agenda_service
from app.modules.catalogs import rules as catalogs_rules
from app.modules.catalogs import service as catalogs_service
from app.modules.patients.models import Patient
from app.voice.context import ScreenContext
from app.voice.dialogue import _clinic_zoneinfo, _local_day_bounds_utc

# Tope para los pacientes agendados hoy: `hotwords` de faster-whisper no
# tiene el limite de ~224 tokens de `initial_prompt` (sec. 3 del doc 05), pero
# una sucursal con una agenda muy llena no deberia mandar una lista sin tope.
_MAX_TODAY_PATIENT_NAMES = 50


async def contextual_terms(
    db: AsyncSession, *, clinic_id: uuid.UUID, context: ScreenContext
) -> tuple[str, ...]:
    terms: set[str] = set()

    for catalog_type in catalogs_rules.CATALOG_TYPES:
        items = await catalogs_service.list_items(
            db, clinic_id=clinic_id, catalog_type=catalog_type
        )
        terms.update(item.name.lower() for item in items)

    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    starts_from, starts_to = _local_day_bounds_utc(tz, today)
    today_appointments = await agenda_service.list_appointments(
        db, clinic_id=clinic_id, starts_from=starts_from, starts_to=starts_to
    )
    for appointment in today_appointments[:_MAX_TODAY_PATIENT_NAMES]:
        full_name = appointment.get("patient_full_name")
        if full_name:
            terms.add(str(full_name).lower())

    if context.patient_id:
        patient = await db.get(Patient, uuid.UUID(context.patient_id))
        if patient is not None:
            terms.add(patient.full_name.lower())

    return tuple(sorted(terms))
