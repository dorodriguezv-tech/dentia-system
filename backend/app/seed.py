"""Datos ficticios de arranque (CLAUDE.md sec. 5: nunca datos reales de pacientes).

Uso: python -m app.seed
Crea una organizacion y una sucursal de ejemplo, un admin_clinica (con MFA
pendiente de configurar, ver regla de CLAUDE.md sec. 5) y un odontologo.
Es idempotente: si el admin ya existe, no hace nada.
"""

import asyncio
import random
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.agenda import service as agenda_service
from app.modules.agenda.models import Provider, Resource
from app.modules.agenda.schemas import (
    AppointmentCreateRequest,
    ProviderCreateRequest,
    ResourceCreateRequest,
    StatusChangeRequest,
    WorkingHoursCreateRequest,
)
from app.modules.catalogs import service as catalogs_service
from app.modules.catalogs.schemas import CatalogItemCreateRequest
from app.modules.diagnosis import service as diagnosis_service
from app.modules.diagnosis.schemas import DiagnosisCreateRequest
from app.modules.documents import service as documents_service
from app.modules.documents.schemas import DocumentTemplateCreateRequest, TemplateCode
from app.modules.encounters import service as encounters_service
from app.modules.encounters.schemas import (
    ClinicalNoteCreateRequest,
    CorrectNoteRequest,
    EncounterCreateRequest,
    FinalizeNoteRequest,
)
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic
from app.modules.odontogram import service as odontogram_service
from app.modules.odontogram.schemas import ToothFindingCreateRequest
from app.modules.odontological_history import rules as odontological_history_rules
from app.modules.patients import service as patients_service
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.pediatric_history import rules as pediatric_history_rules
from app.modules.records import service as records_service
from app.modules.records.schemas import (
    AllergyCreateRequest,
    MedicalHistoryCreateRequest,
    MedicationCreateRequest,
    VitalSignsCreateRequest,
)
from app.modules.treatment import service as treatment_service
from app.modules.treatment.schemas import (
    AcceptPlanRequest,
    ItemCreateRequest,
    PhaseCreateRequest,
    PlanCreateRequest,
    ProcedureCatalogCreateRequest,
    ProcedurePerformedCreateRequest,
)
from app.modules.treatment.schemas import StatusChangeRequest as TreatmentStatusChangeRequest

fake = Faker("es_MX")

# Fase A (rediseno del expediente, docs/clinica): valores de ejemplo para los
# campos compartidos nuevos de Patient -- Faker no trae un "provider" de tipo de
# sangre/escolaridad, asi que se elige al azar de estas listas fijas (mismo
# criterio que `sex=random.choice(["F", "M", None])`, ya existente).
_BLOOD_TYPES = ("O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-")
_EDUCATION_LEVELS = ("primaria", "secundaria", "bachillerato", "licenciatura", "posgrado")
_MARITAL_STATUSES = ("soltero", "casado", "concubinato")

ADMIN_EMAIL = "admin@dentalcare-demo.mx"
ODONTOLOGO_EMAIL = "odontologo@dentalcare-demo.mx"
RECEPCION_EMAIL = "recepcion@dentalcare-demo.mx"
CAJA_EMAIL = "caja@dentalcare-demo.mx"
DEMO_PASSWORD = "Dentia2025!"
PATIENT_COUNT = 50


async def _seed_patients(
    db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID
) -> list[Patient]:
    patients = []
    for _ in range(PATIENT_COUNT):
        data = PatientCreateRequest(
            first_name=fake.first_name(),
            last_name_paternal=fake.last_name(),
            last_name_maternal=fake.last_name(),
            date_of_birth=fake.date_of_birth(minimum_age=1, maximum_age=90),
            sex=random.choice(["F", "M", None]),
            phone=fake.phone_number(),
            email=fake.unique.email(),
            address=fake.address().replace("\n", ", "),
            birth_place=fake.city(),
            blood_type=random.choice(_BLOOD_TYPES),
            education_level=random.choice(_EDUCATION_LEVELS),
            can_read_write=random.choice([True, True, True, False]),
            religion=fake.random_element(elements=("catolica", "cristiana", "ninguna", "otra")),
            occupation=fake.job(),
            marital_status=random.choice(_MARITAL_STATUSES),
        )
        patient = await patients_service.create_patient(
            db, clinic_id=clinic_id, data=data, actor_id=actor_id
        )
        patients.append(patient)
    return patients


async def _seed_clinical_records(
    db: AsyncSession, *, clinic_id: uuid.UUID, professional_id: uuid.UUID, patients: list[Patient]
) -> None:
    """Expediente de muestra (Fase 4) para los primeros pacientes sembrados."""

    # Paciente 1: alergia severa + medicamento de riesgo + antecedente -> varias alertas
    # derivadas, mas una atencion con nota SOAP finalizada (con content_hash).
    p1 = patients[0]
    encounter1 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=p1.id, chief_complaint="Dolor al frio en el lado inferior izquierdo"
        ),
        professional_id=professional_id,
    )
    await records_service.create_allergy(
        db,
        clinic_id=clinic_id,
        patient_id=p1.id,
        data=AllergyCreateRequest(
            encounter_id=encounter1.id,
            substance="Penicilina",
            reaction="Urticaria",
            severity="severa",
        ),
        actor_id=professional_id,
    )
    await records_service.create_medication(
        db,
        clinic_id=clinic_id,
        patient_id=p1.id,
        data=MedicationCreateRequest(
            encounter_id=encounter1.id, name="Warfarina", dose="5mg", frequency="Cada 24 horas"
        ),
        actor_id=professional_id,
    )
    await records_service.create_history(
        db,
        clinic_id=clinic_id,
        patient_id=p1.id,
        data=MedicalHistoryCreateRequest(
            encounter_id=encounter1.id,
            category="heredofamiliar",
            text="Padre con diabetes tipo 2",
        ),
        actor_id=professional_id,
    )
    await records_service.create_vital_signs(
        db,
        clinic_id=clinic_id,
        patient_id=p1.id,
        data=VitalSignsCreateRequest(
            encounter_id=encounter1.id, bp_systolic=118, bp_diastolic=76, heart_rate=70
        ),
        actor_id=professional_id,
    )
    note1 = await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter1.id,
        data=ClinicalNoteCreateRequest(
            soap_s="Dolor al frio en el lado inferior izquierdo",
            soap_o="Caries oclusal y distal en pieza 36",
            soap_a="Pulpitis reversible en organo dentario 36",
            soap_p="Resina en pieza 36. Control en 15 dias.",
        ),
        author_id=professional_id,
    )
    await encounters_service.finalize_note(
        db,
        clinic_id=clinic_id,
        note_id=note1.id,
        data=FinalizeNoteRequest(alerts_acknowledged=True),
        actor_id=professional_id,
    )

    # Odontograma (Fase 5) de la paciente 1: caries oclusal en 36 que ya se trato con
    # resina (demuestra la cadena supersedes_id/is_current, regla 5), caries distal en
    # 36 todavia activa (misma pieza, superficie distinta) y una pieza ausente (18).
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=p1.id,
            encounter_id=encounter1.id,
            tooth_fdi=36,
            surface="O",
            finding_code="caries",
        ),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=p1.id,
            encounter_id=encounter1.id,
            tooth_fdi=36,
            surface="O",
            finding_code="restauracion",
            material="resina",
        ),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=p1.id,
            encounter_id=encounter1.id,
            tooth_fdi=36,
            surface="D",
            finding_code="caries",
        ),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=p1.id, encounter_id=encounter1.id, tooth_fdi=18, finding_code="ausente"
        ),
        actor_id=professional_id,
    )

    # Paciente 2: atencion con nota todavia en borrador (autoguardado en curso).
    p2 = patients[1]
    encounter2 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(patient_id=p2.id, chief_complaint="Revision de rutina"),
        professional_id=professional_id,
    )
    await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter2.id,
        data=ClinicalNoteCreateRequest(soap_s="Sin dolor. Acude a revision semestral."),
        author_id=professional_id,
    )

    # Paciente 3: nota finalizada y despues corregida (muestra version 1 CORRECTED + 2 DRAFT).
    p3 = patients[2]
    encounter3 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(patient_id=p3.id, chief_complaint="Sensibilidad en pieza 46"),
        professional_id=professional_id,
    )
    note3 = await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter3.id,
        data=ClinicalNoteCreateRequest(
            soap_s="Sensibilidad al masticar",
            soap_a="Caries oclusal en pieza 46",
            soap_p="Resina en pieza 46",
        ),
        author_id=professional_id,
    )
    await encounters_service.finalize_note(
        db,
        clinic_id=clinic_id,
        note_id=note3.id,
        data=FinalizeNoteRequest(alerts_acknowledged=True),
        actor_id=professional_id,
    )
    await encounters_service.correct_note(
        db,
        clinic_id=clinic_id,
        note_id=note3.id,
        data=CorrectNoteRequest(
            reason="Faltaba registrar que tambien se afecto la superficie distal"
        ),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=p3.id,
            encounter_id=encounter3.id,
            tooth_fdi=46,
            surface="O",
            finding_code="caries",
        ),
        actor_id=professional_id,
    )


async def _seed_agenda(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    admin_id: uuid.UUID,
    odontologo_id: uuid.UUID,
    patients: list[Patient],
) -> tuple[Provider, Resource]:
    """Agenda de muestra (Fase 6): un profesional agendable, un gabinete, horario
    laboral abierto toda la semana y citas en distintos estados para ver el
    calendario poblado (reservada, confirmada y una en la semana siguiente)."""
    provider, _name = await agenda_service.create_provider(
        db,
        clinic_id=clinic_id,
        data=ProviderCreateRequest(user_id=odontologo_id, color="#2BB3A3"),
        actor_id=admin_id,
    )
    resource = await agenda_service.create_resource(
        db, clinic_id=clinic_id, data=ResourceCreateRequest(name="Gabinete 1"), actor_id=admin_id
    )

    # Horario de la clinica: abierto los 7 dias de la semana, sin restriccion de
    # hora (decision del operador -- antes era lunes a viernes con hora de
    # comida y sabado medio dia). El horario sigue siendo informativo nada mas
    # (sombrea el calendario, no bloquea agendar, ver docstring de
    # ProviderWorkingHours); el admin_clinica puede ajustarlo por profesional
    # desde Configuracion -> Horarios en cualquier momento.
    for weekday in range(7):  # lunes (0) a domingo (6)
        await agenda_service.create_working_hours(
            db,
            clinic_id=clinic_id,
            provider_id=provider.id,
            data=WorkingHoursCreateRequest(
                weekday=weekday, start_time=time(0, 0), end_time=time(23, 59)
            ),
        )

    # .astimezone() (no UTC) para que .replace(hour=...) fije la hora de pared local
    # de la maquina, no 10:00 UTC (que seria la madrugada en America/Mexico_City).
    now = datetime.now().astimezone()
    tomorrow_10am = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    tomorrow_11am = tomorrow_10am.replace(hour=11)
    next_week_930am = (now + timedelta(days=7)).replace(hour=9, minute=30, second=0, microsecond=0)

    await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patients[3].id,
            provider_id=provider.id,
            resource_id=resource.id,
            appointment_type="consulta",
            starts_at=tomorrow_10am,
        ),
        actor_id=admin_id,
    )

    confirmada, _w = await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patients[4].id,
            provider_id=provider.id,
            resource_id=resource.id,
            appointment_type="limpieza",
            starts_at=tomorrow_11am,
        ),
        actor_id=admin_id,
    )
    await agenda_service.change_status(
        db,
        clinic_id=clinic_id,
        appointment_id=confirmada.id,
        data=StatusChangeRequest(status="CONFIRMADA"),
        actor_id=admin_id,
    )

    await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patients[5].id,
            provider_id=provider.id,
            appointment_type="urgencia",
            starts_at=next_week_930am,
        ),
        actor_id=admin_id,
    )

    return provider, resource


def _next_weekday(base: datetime, target_weekday: int) -> datetime:
    """Proxima fecha (estrictamente despues de `base`, nunca el mismo dia) que
    caiga en `target_weekday` (0=lunes .. 6=domingo, igual convencion que
    ProviderWorkingHours.weekday)."""
    days_ahead = target_weekday - base.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return base + timedelta(days=days_ahead)


async def _seed_example_patient(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    admin_id: uuid.UUID,
    professional_id: uuid.UUID,
    provider_id: uuid.UUID,
    resource_id: uuid.UUID,
) -> None:
    """Paciente de ejemplo (a peticion del operador) con expediente completo:
    varias consultas, cada una con nota SOAP finalizada, un odontograma con
    varios trabajos y observaciones en distintas piezas, alergia/medicamento/
    signos vitales/diagnostico, y un plan de tratamiento (2 fases) llevado hasta
    TERMINADO -- para tener algo representativo que mostrar sin tener que armar
    el expediente a mano. Trae ademas dos citas pasadas (una TERMINADA, una
    NO_SHOW, para ver los dos estados de asistencia) y dos citas futuras en dias
    fijos de la semana (proximo lunes 9:00, proximo martes 11:00), pedidas
    explicitamente para verlas pobladas en la agenda. Requiere que el catalogo de
    procedimientos ya exista (ver orden de _seed_treatment en seed()).
    """
    patient = await patients_service.create_patient(
        db,
        clinic_id=clinic_id,
        data=PatientCreateRequest(
            first_name="Roberto",
            last_name_paternal="Fernandez",
            last_name_maternal="Castillo",
            date_of_birth=date(1985, 6, 12),
            sex="M",
            phone="555-010-2030",
            email="roberto.fernandez.ejemplo@example.com",
            address="Av. Reforma 123, CDMX",
        ),
        actor_id=admin_id,
    )

    # Consulta 1: valoracion inicial -- caries en 16, antecedente relevante.
    encounter1 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=patient.id, chief_complaint="Dolor al masticar del lado derecho"
        ),
        professional_id=professional_id,
    )
    await records_service.create_history(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=MedicalHistoryCreateRequest(
            encounter_id=encounter1.id,
            category="odontologico",
            text="Tratamiento de ortodoncia hace 10 anos, sin complicaciones.",
        ),
        actor_id=professional_id,
    )
    # Alergia, medicamento y signos vitales de muestra -- para que el expediente
    # completo tenga algo que mostrar en cada seccion, no solo en antecedentes.
    await records_service.create_allergy(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=AllergyCreateRequest(
            encounter_id=encounter1.id,
            substance="Penicilina",
            reaction="Urticaria",
            severity="moderada",
        ),
        actor_id=professional_id,
    )
    await records_service.create_medication(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=MedicationCreateRequest(
            encounter_id=encounter1.id,
            name="Losartan",
            dose="50mg",
            frequency="Cada 24 horas",
        ),
        actor_id=professional_id,
    )
    await records_service.create_vital_signs(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=VitalSignsCreateRequest(
            encounter_id=encounter1.id, bp_systolic=124, bp_diastolic=80, heart_rate=72
        ),
        actor_id=professional_id,
    )
    note1 = await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter1.id,
        data=ClinicalNoteCreateRequest(
            soap_s="Refiere dolor al masticar del lado derecho desde hace 3 dias.",
            soap_o="Caries oclusal profunda en pieza 16. Sensible a la percusion.",
            soap_a="Caries profunda en organo dentario 16, probable compromiso pulpar.",
            soap_p="Se propone endodoncia en pieza 16, seguida de corona. Se explica al"
            " paciente el plan y acepta continuar.",
        ),
        author_id=professional_id,
    )
    await encounters_service.finalize_note(
        db,
        clinic_id=clinic_id,
        note_id=note1.id,
        data=FinalizeNoteRequest(alerts_acknowledged=True),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter1.id,
            tooth_fdi=16,
            surface="O",
            finding_code="caries",
        ),
        actor_id=professional_id,
    )

    # Consulta 2: se realiza la endodoncia acordada en la consulta 1.
    encounter2 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=patient.id, chief_complaint="Continuacion de tratamiento en pieza 16"
        ),
        professional_id=professional_id,
    )
    note2 = await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter2.id,
        data=ClinicalNoteCreateRequest(
            soap_s="Acude para continuar tratamiento, sin dolor en este momento.",
            soap_o="Pieza 16 aislada con dique de hule. Conductos localizados.",
            soap_a="Pulpitis irreversible en organo dentario 16, confirmada.",
            soap_p="Endodoncia en pieza 16 realizada en esta cita. Se programa corona en"
            " proxima visita. Paciente tolero bien el procedimiento.",
        ),
        author_id=professional_id,
    )
    await encounters_service.finalize_note(
        db,
        clinic_id=clinic_id,
        note_id=note2.id,
        data=FinalizeNoteRequest(alerts_acknowledged=True),
        actor_id=professional_id,
    )
    # La caries previa en 16-O queda resuelta: se registra la endodoncia con
    # la MISMA superficie para que reemplace ese hallazgo (regla 5: solo uno
    # vigente por pieza y superficie -- "vigente" se evalua pieza+superficie
    # exactas, asi que hay que repetir la superficie para encadenar el
    # historial en vez de dejar la caries vigente en paralelo).
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter2.id,
            tooth_fdi=16,
            surface="O",
            finding_code="endodoncia",
        ),
        actor_id=professional_id,
    )
    # Caries nueva, activa, en otra pieza -- para que el odontograma muestre
    # mas de un trabajo a la vez.
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter2.id,
            tooth_fdi=26,
            surface="O",
            finding_code="caries",
        ),
        actor_id=professional_id,
    )
    # Sellador preventivo en una pieza sana, para mostrar un hallazgo que no
    # es una caries ni una restauracion.
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter2.id,
            tooth_fdi=36,
            surface="O",
            finding_code="sellador",
        ),
        actor_id=professional_id,
    )
    await diagnosis_service.create_diagnosis(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=DiagnosisCreateRequest(
            encounter_id=encounter2.id,
            tooth_fdi=26,
            surface="O",
            code="caries",
            text="Caries oclusal en 26, se propone restauracion con resina.",
        ),
        actor_id=professional_id,
    )

    # Consulta 3: se coloca la corona en 16 y se resuelve la caries de 26.
    encounter3 = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=patient.id, chief_complaint="Colocacion de corona y revision"
        ),
        professional_id=professional_id,
    )
    note3 = await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter3.id,
        data=ClinicalNoteCreateRequest(
            soap_s="Sin molestias desde la endodoncia.",
            soap_o="Pieza 16 asintomatica. Caries oclusal en 26 confirmada al explorar.",
            soap_a="Organo dentario 16 listo para restauracion definitiva. Caries activa en 26.",
            soap_p="Se cementa corona en pieza 16. Se coloca resina en pieza 26. Proxima"
            " revision en 6 meses.",
        ),
        author_id=professional_id,
    )
    await encounters_service.finalize_note(
        db,
        clinic_id=clinic_id,
        note_id=note3.id,
        data=FinalizeNoteRequest(alerts_acknowledged=True),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter3.id,
            tooth_fdi=16,
            surface="O",
            finding_code="corona",
        ),
        actor_id=professional_id,
    )
    await odontogram_service.create_finding(
        db,
        clinic_id=clinic_id,
        data=ToothFindingCreateRequest(
            patient_id=patient.id,
            encounter_id=encounter3.id,
            tooth_fdi=26,
            surface="O",
            finding_code="restauracion",
            material="resina",
        ),
        actor_id=professional_id,
    )

    # Plan de tratamiento de muestra (misma pieza 16 que el odontograma de arriba):
    # dos fases, ambas presentadas, aceptadas, realizadas y el plan marcado como
    # TERMINADO -- para que se vea un plan completo con su situacion, quien
    # atiende y que ya concluyo, no solo uno en borrador.
    plan = await treatment_service.create_plan(
        db,
        clinic_id=clinic_id,
        data=PlanCreateRequest(
            patient_id=patient.id, encounter_id=encounter1.id, title="Rehabilitacion pieza 16"
        ),
        actor_id=professional_id,
    )
    plan_phase1 = await treatment_service.add_phase(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=PhaseCreateRequest(name="Fase 1: endodoncia", sort_order=1, priority="alta"),
        actor_id=professional_id,
    )
    plan_item1 = await treatment_service.add_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        phase_id=plan_phase1.id,
        data=ItemCreateRequest(
            encounter_id=encounter2.id,
            tooth_fdi=16,
            surface="O",
            procedure_code="endodoncia_unirradicular",
            finding_code="endodoncia",
        ),
        actor_id=professional_id,
    )
    plan_phase2 = await treatment_service.add_phase(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=PhaseCreateRequest(name="Fase 2: corona", sort_order=2, priority="media"),
        actor_id=professional_id,
    )
    plan_item2 = await treatment_service.add_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        phase_id=plan_phase2.id,
        data=ItemCreateRequest(
            encounter_id=encounter3.id,
            tooth_fdi=16,
            surface="O",
            procedure_code="corona_metal_porcelana",
            finding_code="corona",
        ),
        actor_id=professional_id,
    )
    await treatment_service.change_status(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=TreatmentStatusChangeRequest(status="PRESENTADO"),
        actor_id=professional_id,
    )
    await treatment_service.accept_plan(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=AcceptPlanRequest(
            accepted_item_ids=[plan_item1.id, plan_item2.id], accepted_by_name=patient.full_name
        ),
        actor_id=professional_id,
    )
    await treatment_service.register_performed(
        db,
        clinic_id=clinic_id,
        data=ProcedurePerformedCreateRequest(
            patient_id=patient.id, encounter_id=encounter2.id, planned_id=plan_item1.id
        ),
        actor_id=professional_id,
    )
    await treatment_service.register_performed(
        db,
        clinic_id=clinic_id,
        data=ProcedurePerformedCreateRequest(
            patient_id=patient.id, encounter_id=encounter3.id, planned_id=plan_item2.id
        ),
        actor_id=professional_id,
    )
    await treatment_service.change_status(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=TreatmentStatusChangeRequest(status="EN_PROGRESO"),
        actor_id=professional_id,
    )
    await treatment_service.change_status(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=TreatmentStatusChangeRequest(status="TERMINADO"),
        actor_id=professional_id,
    )

    # Dos citas pasadas, para que el historial de citas del paciente muestre los
    # estados de asistencia (una atendida, una no-show) y no solo reservas futuras.
    now = datetime.now().astimezone()
    past_attended_at = (now - timedelta(days=12)).replace(
        hour=10, minute=30, second=0, microsecond=0
    )
    past_no_show_at = (now - timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0)

    past_attended, _w1 = await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patient.id,
            provider_id=provider_id,
            resource_id=resource_id,
            appointment_type="consulta",
            starts_at=past_attended_at,
            notes="Valoracion inicial, paciente con expediente de ejemplo.",
        ),
        actor_id=admin_id,
    )
    await agenda_service.change_status(
        db,
        clinic_id=clinic_id,
        appointment_id=past_attended.id,
        data=StatusChangeRequest(status="EN_ATENCION"),
        actor_id=professional_id,
    )
    await agenda_service.change_status(
        db,
        clinic_id=clinic_id,
        appointment_id=past_attended.id,
        data=StatusChangeRequest(status="TERMINADA"),
        actor_id=professional_id,
    )

    past_no_show, _w2 = await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patient.id,
            provider_id=provider_id,
            resource_id=resource_id,
            appointment_type="limpieza",
            starts_at=past_no_show_at,
            notes="Limpieza programada, paciente con expediente de ejemplo.",
        ),
        actor_id=admin_id,
    )
    await agenda_service.change_status(
        db,
        clinic_id=clinic_id,
        appointment_id=past_no_show.id,
        data=StatusChangeRequest(status="NO_SHOW", reason="El paciente no se presento ni aviso."),
        actor_id=admin_id,
    )

    # Dos citas futuras, pedidas explicitamente: proximo lunes 9:00 y proximo
    # martes 11:00 (nunca el mismo dia de hoy, aunque hoy sea lunes o martes --
    # ver _next_weekday). Quedan en RESERVADA, como corresponde a una cita que
    # todavia no ocurre.
    next_monday_9am = _next_weekday(now, 0).replace(hour=9, minute=0, second=0, microsecond=0)
    next_tuesday_11am = _next_weekday(now, 1).replace(hour=11, minute=0, second=0, microsecond=0)

    await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patient.id,
            provider_id=provider_id,
            resource_id=resource_id,
            appointment_type="consulta",
            starts_at=next_monday_9am,
            notes="Revision de control, paciente con expediente de ejemplo.",
        ),
        actor_id=admin_id,
    )
    await agenda_service.create_appointment(
        db,
        clinic_id=clinic_id,
        data=AppointmentCreateRequest(
            patient_id=patient.id,
            provider_id=provider_id,
            resource_id=resource_id,
            appointment_type="limpieza",
            starts_at=next_tuesday_11am,
            notes="Limpieza de control, paciente con expediente de ejemplo.",
        ),
        actor_id=admin_id,
    )


async def _seed_treatment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    admin_id: uuid.UUID,
    professional_id: uuid.UUID,
    patients: list[Patient],
) -> None:
    """Catalogo de procedimientos, un diagnostico y un plan de tratamiento de muestra
    (Fase 7): fase 1 (endodoncia en 46) ya aceptada y realizada -- demuestra que lo
    planificado no se edita (regla 3) y que se genera un cargo sugerido, nunca un pago
    (regla 4) -- y fase 2 (corona) todavia solo planificada."""
    catalog_items = [
        ("consulta_valoracion", "Consulta de valoracion", "300.00"),
        ("resina_oclusal", "Resina oclusal", "650.00"),
        ("limpieza_dental", "Limpieza dental (profilaxis)", "450.00"),
        ("endodoncia_unirradicular", "Endodoncia unirradicular", "2800.00"),
        ("corona_metal_porcelana", "Corona metal-porcelana", "4500.00"),
    ]
    for code, name, price in catalog_items:
        await treatment_service.create_procedure_catalog_item(
            db,
            clinic_id=clinic_id,
            data=ProcedureCatalogCreateRequest(code=code, name=name, default_price=Decimal(price)),
            actor_id=admin_id,
        )

    patient = patients[0]
    encounter = await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=patient.id, chief_complaint="Valoracion de plan de tratamiento"
        ),
        professional_id=professional_id,
    )

    await diagnosis_service.create_diagnosis(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        data=DiagnosisCreateRequest(
            encounter_id=encounter.id,
            tooth_fdi=46,
            surface="O",
            code="caries",
            text="Caries oclusal profunda en 46, requiere tratamiento de conductos",
        ),
        actor_id=professional_id,
    )

    plan = await treatment_service.create_plan(
        db,
        clinic_id=clinic_id,
        data=PlanCreateRequest(
            patient_id=patient.id, encounter_id=encounter.id, title="Rehabilitacion pieza 46"
        ),
        actor_id=professional_id,
    )
    phase1 = await treatment_service.add_phase(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=PhaseCreateRequest(name="Fase 1: endodoncia", sort_order=1, priority="alta"),
        actor_id=professional_id,
    )
    item1 = await treatment_service.add_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        phase_id=phase1.id,
        data=ItemCreateRequest(
            encounter_id=encounter.id,
            tooth_fdi=46,
            surface="O",
            procedure_code="endodoncia_unirradicular",
            finding_code="endodoncia",
        ),
        actor_id=professional_id,
    )
    phase2 = await treatment_service.add_phase(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=PhaseCreateRequest(name="Fase 2: restauracion final", sort_order=2, priority="media"),
        actor_id=professional_id,
    )
    await treatment_service.add_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        phase_id=phase2.id,
        data=ItemCreateRequest(
            encounter_id=encounter.id,
            tooth_fdi=46,
            procedure_code="corona_metal_porcelana",
            finding_code="corona",
        ),
        actor_id=professional_id,
    )

    await treatment_service.change_status(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=TreatmentStatusChangeRequest(status="PRESENTADO"),
        actor_id=professional_id,
    )
    await treatment_service.accept_plan(
        db,
        clinic_id=clinic_id,
        plan_id=plan.id,
        data=AcceptPlanRequest(accepted_item_ids=[item1.id], accepted_by_name=patient.full_name),
        actor_id=professional_id,
    )
    await treatment_service.register_performed(
        db,
        clinic_id=clinic_id,
        data=ProcedurePerformedCreateRequest(
            patient_id=patient.id, encounter_id=encounter.id, planned_id=item1.id
        ),
        actor_id=professional_id,
    )


# Correccion A6 (docs/06_INSTRUCCIONES...): sin esto, el selector de plantillas al
# firmar un consentimiento quedaba vacio -- "Firmar y generar PDF" nunca podia
# habilitarse porque no habia nada que elegir. "Ejemplo" en el nombre porque el texto
# legal real lo debe redactar/validar la clinica (ver docs/PENDIENTES_CLINICOS.md).
DOCUMENT_TEMPLATE_SEEDS: list[tuple[TemplateCode, str, str]] = [
    (
        "general",
        "Ejemplo — validar con la clinica: consentimiento general",
        "<p>Yo, {{paciente.nombre}}, de {{paciente.edad}} anos, autorizo a "
        "{{clinica.nombre}} y al profesional {{profesional.nombre}} (cedula "
        "profesional {{profesional.cedula}}) a realizar el tratamiento dental que "
        "se me explico, incluidos sus riesgos y alternativas. Fecha: {{fecha}}.</p>",
    ),
    (
        "extraccion",
        "Ejemplo — validar con la clinica: extraccion dental",
        "<p>Autorizo a {{profesional.nombre}} (cedula profesional "
        "{{profesional.cedula}}) a realizar la extraccion de la pieza indicada en "
        "mi expediente. Entiendo los riesgos (sangrado, infeccion, dano a piezas "
        "vecinas) y las alternativas de tratamiento. Procedimiento: "
        "{{procedimiento.nombre}}. Fecha: {{fecha}}.</p>",
    ),
    (
        "endodoncia",
        "Ejemplo — validar con la clinica: endodoncia (tratamiento de conductos)",
        "<p>Autorizo a {{profesional.nombre}} (cedula profesional "
        "{{profesional.cedula}}) a realizar el tratamiento de conductos "
        "(endodoncia) indicado en mi plan de tratamiento "
        "{{plan.titulo}}. Entiendo que puede requerir mas de una cita y que existe "
        "riesgo de fractura o perdida de la pieza. Fecha: {{fecha}}.</p>",
    ),
    (
        "anestesia",
        "Ejemplo — validar con la clinica: anestesia local",
        "<p>Autorizo la aplicacion de anestesia local para mi tratamiento en "
        "{{clinica.nombre}}. He informado al profesional {{profesional.nombre}} "
        "(cedula profesional {{profesional.cedula}}) de mis alergias y "
        "antecedentes medicos conocidos. Fecha: {{fecha}}.</p>",
    ),
]


async def _seed_document_templates(
    db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID
) -> None:
    for code, name, html_content in DOCUMENT_TEMPLATE_SEEDS:
        await documents_service.create_template_version(
            db,
            clinic_id=clinic_id,
            data=DocumentTemplateCreateRequest(code=code, name=name, html_content=html_content),
            actor_id=actor_id,
        )


# Correccion B1 (docs/06_INSTRUCCIONES..., Parte B): hasta esta fase, estos catalogos
# vivian fijos en codigo (agenda/rules.py, odontogram/finding_catalog.py,
# diagnosis/rules.py, records/rules.py) -- un administrador no podia agregar ni
# desactivar un elemento sin pedir un cambio de codigo. Misma lista que usa
# tests/conftest.py (fixture `clinic`, para que toda prueba tenga un catalogo
# realista) y, duplicada a proposito (una migracion no debe depender del codigo de
# la aplicacion), la migracion de backfill 4d7a2e9c15f3.
# (catalog_type, code, name, sort_order, extra)
CATALOG_SEEDS: list[tuple[str, str, str, int, dict[str, object]]] = [
    ("appointment_type", "consulta", "Consulta / valoracion", 0, {"default_minutes": 30}),
    ("appointment_type", "limpieza", "Limpieza dental", 1, {"default_minutes": 45}),
    (
        "appointment_type",
        "restauracion",
        "Restauracion (resina/amalgama)",
        2,
        {"default_minutes": 60},
    ),
    ("appointment_type", "endodoncia", "Endodoncia", 3, {"default_minutes": 90}),
    ("appointment_type", "extraccion", "Extraccion", 4, {"default_minutes": 45}),
    (
        "appointment_type",
        "ortodoncia_control",
        "Control de ortodoncia",
        5,
        {"default_minutes": 20},
    ),
    ("appointment_type", "protesis", "Protesis", 6, {"default_minutes": 60}),
    ("appointment_type", "urgencia", "Urgencia", 7, {"default_minutes": 30}),
    (
        "odontogram_finding",
        "sano",
        "Sano",
        0,
        {"color": "#A9C6B8", "symbol": "", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "caries",
        "Caries",
        1,
        {"color": "#D64545", "symbol": "C", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "restauracion",
        "Restauracion",
        2,
        {"color": "#4A90C2", "symbol": "R", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "corona",
        "Corona",
        3,
        {"color": "#E0A100", "symbol": "CO", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "endodoncia",
        "Endodoncia",
        4,
        {"color": "#7B5EA7", "symbol": "E", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "ausente",
        "Ausente",
        5,
        # Negro (antes gris #8C8C8C): leyenda oficial de docs/clinica, "Negro: dientes
        # ausentes o restos radiculares" (Fase B).
        {"color": "#1A1A1A", "symbol": "X", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "extraccion_indicada",
        "Extraccion indicada",
        6,
        {"color": "#D64545", "symbol": "XI", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "implante",
        "Implante",
        7,
        {"color": "#2BB3A3", "symbol": "IM", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "protesis_fija",
        "Protesis fija",
        8,
        {"color": "#3A7FC1", "symbol": "PF", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "sellador",
        "Sellador",
        9,
        # Reasignado de verde (ahora de "biopelicula_tartaro") a magenta: leyenda
        # oficial de docs/clinica reserva el verde para biopelicula/tartaro (Fase B).
        {"color": "#A8407D", "symbol": "S", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "fractura",
        "Fractura",
        10,
        {"color": "#B8460E", "symbol": "FX", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "movilidad",
        "Movilidad",
        11,
        {"color": "#C77D1E", "symbol": "MO", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "biopelicula_tartaro",
        "Biopelicula y tartaro dental",
        12,
        # Hallazgo nuevo (Fase B, leyenda oficial de docs/clinica: "Verde: biopelicula y
        # tartaro dental"): reusa el verde que antes tenia "sellador".
        {"color": "#6AB04C", "symbol": "BT", "requires_surface": True},
    ),
    ("diagnosis", "caries", "Caries dental", 0, {}),
    ("diagnosis", "caries_recurrente", "Caries recurrente", 1, {}),
    ("diagnosis", "pulpitis_reversible", "Pulpitis reversible", 2, {}),
    ("diagnosis", "pulpitis_irreversible", "Pulpitis irreversible", 3, {}),
    ("diagnosis", "necrosis_pulpar", "Necrosis pulpar", 4, {}),
    ("diagnosis", "absceso_periapical", "Absceso periapical", 5, {}),
    ("diagnosis", "gingivitis", "Gingivitis", 6, {}),
    ("diagnosis", "periodontitis", "Periodontitis", 7, {}),
    ("diagnosis", "fractura_dental", "Fractura dental", 8, {}),
    ("diagnosis", "edentulismo_parcial", "Edentulismo parcial", 9, {}),
    ("diagnosis", "maloclusion", "Maloclusion", 10, {}),
    ("diagnosis", "sin_hallazgos", "Sin hallazgos patologicos", 11, {}),
    ("history_category", "heredofamiliar", "Heredofamiliar", 0, {}),
    ("history_category", "personal_patologico", "Personal patologico", 1, {}),
    ("history_category", "personal_no_patologico", "Personal no patologico", 2, {}),
    ("history_category", "odontologico", "Odontologico", 3, {}),
    ("history_category", "habito", "Habito", 4, {}),
    ("history_category", "factor_riesgo", "Factor de riesgo", 5, {}),
    (
        "condition_alert_keyword",
        "diabetes",
        "diabetes",
        0,
        {"alert_label": "Paciente con diabetes"},
    ),
    (
        "condition_alert_keyword",
        "embarazo",
        "embarazo",
        1,
        {"alert_label": "Paciente embarazada"},
    ),
    (
        "condition_alert_keyword",
        "embarazada",
        "embarazada",
        2,
        {"alert_label": "Paciente embarazada"},
    ),
    (
        "condition_alert_keyword",
        "hipertension",
        "hipertension",
        3,
        {"alert_label": "Paciente hipertenso"},
    ),
    (
        "condition_alert_keyword",
        "marcapasos",
        "marcapasos",
        4,
        {"alert_label": "Paciente con marcapasos"},
    ),
    (
        "condition_alert_keyword",
        "hemofilia",
        "hemofilia",
        5,
        {"alert_label": "Paciente con trastorno de coagulacion"},
    ),
    ("condition_alert_keyword", "vih", "vih", 6, {"alert_label": "Paciente con VIH"}),
    (
        "condition_alert_keyword",
        "hepatitis",
        "hepatitis",
        7,
        {"alert_label": "Paciente con hepatitis"},
    ),
    (
        "condition_alert_keyword",
        "epilepsia",
        "epilepsia",
        8,
        {"alert_label": "Paciente con epilepsia"},
    ),
    (
        "condition_alert_keyword",
        "cardiopatia",
        "cardiopatia",
        9,
        {"alert_label": "Paciente con cardiopatia"},
    ),
    (
        "medication_alert_keyword",
        "anticoagulante",
        "anticoagulante",
        0,
        {"alert_label": "Paciente usa anticoagulantes"},
    ),
    (
        "medication_alert_keyword",
        "warfarina",
        "warfarina",
        1,
        {"alert_label": "Paciente usa anticoagulantes (warfarina)"},
    ),
    (
        "medication_alert_keyword",
        "acenocumarina",
        "acenocumarina",
        2,
        {"alert_label": "Paciente usa anticoagulantes (acenocumarina)"},
    ),
    (
        "medication_alert_keyword",
        "rivaroxaban",
        "rivaroxaban",
        3,
        {"alert_label": "Paciente usa anticoagulantes (rivaroxaban)"},
    ),
    (
        "medication_alert_keyword",
        "apixaban",
        "apixaban",
        4,
        {"alert_label": "Paciente usa anticoagulantes (apixaban)"},
    ),
    (
        "medication_alert_keyword",
        "clopidogrel",
        "clopidogrel",
        5,
        {"alert_label": "Paciente usa antiagregantes plaquetarios (clopidogrel)"},
    ),
    (
        "medication_alert_keyword",
        "aspirina",
        "aspirina",
        6,
        {"alert_label": "Paciente usa antiagregantes plaquetarios (aspirina)"},
    ),
    (
        "medication_alert_keyword",
        "insulina",
        "insulina",
        7,
        {"alert_label": "Paciente usa insulina"},
    ),
    (
        "medication_alert_keyword",
        "bifosfonato",
        "bifosfonato",
        8,
        {"alert_label": "Paciente usa bifosfonatos (riesgo de osteonecrosis)"},
    ),
    (
        "medication_alert_keyword",
        "corticoesteroide",
        "corticoesteroide",
        9,
        {"alert_label": "Paciente usa corticoesteroides"},
    ),
    (
        "medication_alert_keyword",
        "inmunosupresor",
        "inmunosupresor",
        10,
        {"alert_label": "Paciente usa inmunosupresores"},
    ),
    # Fase A (rediseno del expediente segun formatos oficiales, docs/clinica):
    # Historia Clinica General. Valores por defecto razonables, pendientes de
    # validar con la clinica real (ver docs/PENDIENTES_CLINICOS.md).
    ("family_relationship", "padre", "Padre", 0, {}),
    ("family_relationship", "madre", "Madre", 1, {}),
    ("family_relationship", "hermano_a", "Hermano(a)", 2, {}),
    ("family_relationship", "abuelo_paterno", "Abuelo paterno", 3, {}),
    ("family_relationship", "abuela_paterna", "Abuela paterna", 4, {}),
    ("family_relationship", "abuelo_materno", "Abuelo materno", 5, {}),
    ("family_relationship", "abuela_materna", "Abuela materna", 6, {}),
    (
        "family_condition",
        "diabetes_mellitus",
        "Diabetes mellitus",
        0,
        {"alert_label": "Antecedente heredofamiliar de diabetes"},
    ),
    (
        "family_condition",
        "hipertension",
        "Hipertension",
        1,
        {"alert_label": "Antecedente heredofamiliar de hipertension"},
    ),
    ("family_condition", "enfermedades_renales", "Enfermedades renales", 2, {}),
    ("family_condition", "ets", "Enfermedades de transmision sexual", 3, {}),
    ("family_condition", "hepatitis_abc", "Hepatitis A, B o C", 4, {}),
    ("family_condition", "cancer", "Cancer", 5, {}),
    ("family_condition", "epilepsia", "Epilepsia", 6, {}),
    ("family_condition", "tuberculosis", "Tuberculosis", 7, {}),
    ("family_condition", "cardiopatias", "Cardiopatias", 8, {}),
    ("family_condition", "artritis", "Artritis", 9, {}),
    ("family_condition", "malformaciones", "Malformaciones congenitas", 10, {}),
    ("family_condition", "discapacidad_fisica", "Discapacidad fisica", 11, {}),
    (
        "family_condition",
        "padecimientos_psicologicos",
        "Padecimientos psicologicos",
        12,
        {},
    ),
    ("family_condition", "alcoholismo", "Alcoholismo", 13, {}),
    ("family_condition", "tabaquismo", "Tabaquismo", 14, {}),
    ("family_condition", "aparentemente_sano", "Aparentemente sano", 15, {}),
    (
        "pathological_condition",
        "diabetes",
        "Diabetes",
        0,
        {"alert_label": "Paciente con diabetes"},
    ),
    (
        "pathological_condition",
        "hipertension",
        "Hipertension",
        1,
        {"alert_label": "Paciente hipertenso"},
    ),
    ("pathological_condition", "enfermedades_renales", "Enfermedades renales", 2, {}),
    ("pathological_condition", "ets", "Enfermedades de transmision sexual", 3, {}),
    (
        "pathological_condition",
        "hepatitis",
        "Hepatitis",
        4,
        {"alert_label": "Paciente con hepatitis"},
    ),
    ("pathological_condition", "cancer", "Cancer", 5, {}),
    (
        "pathological_condition",
        "epilepsia",
        "Epilepsia",
        6,
        {"alert_label": "Paciente con epilepsia"},
    ),
    ("pathological_condition", "tuberculosis", "Tuberculosis", 7, {}),
    (
        "pathological_condition",
        "cardiopatias",
        "Cardiopatias",
        8,
        {"alert_label": "Paciente con cardiopatia"},
    ),
    ("pathological_condition", "artritis", "Artritis", 9, {}),
    ("pathological_condition", "malformaciones", "Malformaciones congenitas", 10, {}),
    ("pathological_condition", "discapacidad_fisica", "Discapacidad fisica", 11, {}),
    (
        "pathological_condition",
        "padecimientos_psicologicos",
        "Padecimientos psicologicos",
        12,
        {},
    ),
    ("pathological_condition", "depresion", "Depresion", 13, {}),
    ("pathological_condition", "varicela", "Varicela", 14, {}),
    ("pathological_condition", "viruela", "Viruela", 15, {}),
    ("pathological_condition", "otro", "Otro", 16, {}),
    ("systems_review_finding", "anemia", "Anemia", 0, {"system": "hematologico"}),
    (
        "systems_review_finding",
        "hemorragias_frecuentes",
        "Hemorragias frecuentes",
        1,
        {"system": "hematologico"},
    ),
    ("systems_review_finding", "transfusiones", "Transfusiones", 2, {"system": "hematologico"}),
    (
        "systems_review_finding",
        "hipertension_cv",
        "Hipertension",
        3,
        {"system": "cardiovascular"},
    ),
    (
        "systems_review_finding",
        "soplo_cardiaco",
        "Soplo cardiaco",
        4,
        {"system": "cardiovascular"},
    ),
    (
        "systems_review_finding",
        "fiebre_reumatica",
        "Fiebre reumatica",
        5,
        {"system": "cardiovascular"},
    ),
    ("systems_review_finding", "arritmias", "Arritmias", 6, {"system": "cardiovascular"}),
    ("systems_review_finding", "convulsiones", "Convulsiones", 7, {"system": "neurologico"}),
    ("systems_review_finding", "desmayos", "Desmayos", 8, {"system": "neurologico"}),
    ("systems_review_finding", "migrana", "Migrana", 9, {"system": "neurologico"}),
    ("systems_review_finding", "paralisis", "Paralisis", 10, {"system": "neurologico"}),
    ("systems_review_finding", "diabetes_endocrino", "Diabetes", 11, {"system": "endocrino"}),
    (
        "systems_review_finding",
        "trastornos_tiroideos",
        "Trastornos tiroideos",
        12,
        {"system": "endocrino"},
    ),
    (
        "systems_review_finding",
        "trastornos_crecimiento",
        "Trastornos del crecimiento",
        13,
        {"system": "endocrino"},
    ),
    ("systems_review_finding", "asma", "Asma", 14, {"system": "respiratorio"}),
    ("systems_review_finding", "bronquitis", "Bronquitis", 15, {"system": "respiratorio"}),
    (
        "systems_review_finding",
        "tuberculosis_resp",
        "Tuberculosis",
        16,
        {"system": "respiratorio"},
    ),
    ("systems_review_finding", "sinusitis", "Sinusitis", 17, {"system": "respiratorio"}),
    (
        "systems_review_finding",
        "infecciones_urinarias",
        "Infecciones urinarias",
        18,
        {"system": "genitourinario"},
    ),
    (
        "systems_review_finding",
        "insuficiencia_renal",
        "Insuficiencia renal",
        19,
        {"system": "genitourinario"},
    ),
    (
        "systems_review_finding",
        "calculos_renales",
        "Calculos renales",
        20,
        {"system": "genitourinario"},
    ),
    # Fase C (rediseno del expediente, docs/clinica): Historia Clinica
    # Odontologica -- craneo, biotipo facial y las preguntas de la anamnesis
    # periodontal (cuestionario de entrevista, no sondeo clinico).
    ("skull_type", "mesocefalo", "Mesocefalo", 0, {}),
    ("skull_type", "braquicefalo", "Braquicefalo", 1, {}),
    ("skull_type", "dolicocefalo", "Dolicocefalo", 2, {}),
    ("facial_biotype", "mesofacial", "Mesofacial", 0, {}),
    ("facial_biotype", "braquifacial", "Braquifacial", 1, {}),
    ("facial_biotype", "dolicofacial", "Dolicofacial", 2, {}),
    *[
        ("periodontal_anamnesis_question", code, text, sort_order, {})
        for sort_order, (code, text) in enumerate(
            odontological_history_rules.PERIODONTAL_ANAMNESIS_QUESTIONS
        )
    ],
    # Fase E (rediseno del expediente, docs/clinica): Historia Clinica
    # Pediatrica -- caracter del paciente, planos terminales y anomalias del
    # odontograma pediatrico (incluye ausente congenito/adquirida, ver nota de
    # correccion en pediatric_history/rules.py -- NO toca `odontogram_finding`).
    ("pediatric_character", "apatico", "Apatico", 0, {}),
    ("pediatric_character", "introvertido_moderado", "Introvertido moderado", 1, {}),
    ("pediatric_character", "inquieto", "Inquieto", 2, {}),
    ("pediatric_character", "irritable", "Irritable", 3, {}),
    ("pediatric_character", "hiperactivo", "Hiperactivo", 4, {}),
    ("pediatric_character", "agresivo", "Agresivo", 5, {}),
    ("terminal_plane", "recto", "Recto", 0, {}),
    ("terminal_plane", "mesial", "Mesial", 1, {}),
    ("terminal_plane", "distal", "Distal", 2, {}),
    *[
        ("pediatric_tooth_anomaly", code, name, sort_order, {})
        for sort_order, (code, name) in enumerate(
            pediatric_history_rules.PEDIATRIC_TOOTH_ANOMALY_OPTIONS
        )
    ],
]


async def _seed_catalogs(db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    for catalog_type, code, name, sort_order, extra in CATALOG_SEEDS:
        await catalogs_service.create_item(
            db,
            clinic_id=clinic_id,
            catalog_type=catalog_type,
            data=CatalogItemCreateRequest(code=code, name=name, sort_order=sort_order, extra=extra),
            actor_id=actor_id,
        )


async def seed() -> None:
    async with async_session_factory() as db:
        existing = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if existing is not None:
            print("El seed ya se aplico antes; no se hace nada.")
            return

        organization = Organization(name="Clinica Dental Demo")
        db.add(organization)
        await db.flush()

        clinic = Clinic(
            organization_id=organization.id,
            name="Sucursal Centro",
            address=fake.address(),
            phone=fake.phone_number(),
        )
        db.add(clinic)
        await db.flush()

        admin_role = (
            await db.execute(select(Role).where(Role.code == "admin_clinica"))
        ).scalar_one()
        odontologo_role = (
            await db.execute(select(Role).where(Role.code == "odontologo"))
        ).scalar_one()
        recepcion_role = (
            await db.execute(select(Role).where(Role.code == "recepcion"))
        ).scalar_one()
        caja_role = (await db.execute(select(Role).where(Role.code == "caja"))).scalar_one()

        admin = User(
            email=ADMIN_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        odontologo = User(
            email=ODONTOLOGO_EMAIL,
            full_name=fake.name(),
            # De ejemplo, para que la vista previa de plantillas de consentimiento y
            # los PDF firmados muestren una cedula real (ahora obligatoria al dar de
            # alta un odontologo/especialista, ver iam/service.py).
            professional_license="DGP1234567",
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        # recepcion y caja (Fase 12): sin estos dos no se puede recorrer el flujo
        # completo paciente->cita->...->pago en el E2E de Playwright, porque
        # billing.write no lo tiene el odontologo (RBAC real,
        # docs/MATRIZ_PERMISOS.md) -- tambien sirven para pruebas manuales.
        recepcion = User(
            email=RECEPCION_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        caja = User(
            email=CAJA_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add_all([admin, odontologo, recepcion, caja])
        await db.flush()

        db.add_all(
            [
                UserClinic(user_id=admin.id, clinic_id=clinic.id, role_id=admin_role.id),
                UserClinic(user_id=odontologo.id, clinic_id=clinic.id, role_id=odontologo_role.id),
                UserClinic(user_id=recepcion.id, clinic_id=clinic.id, role_id=recepcion_role.id),
                UserClinic(user_id=caja.id, clinic_id=clinic.id, role_id=caja_role.id),
            ]
        )
        await db.commit()

        # Los catalogos (history_category, diagnosis, appointment_type, ...) se
        # siembran primero: _seed_clinical_records/_seed_agenda/_seed_treatment
        # crean registros que referencian esos codigos y fallan con
        # INVALID_HISTORY_CATEGORY (u otro catalogo invalido) si todavia no
        # existen en esta sucursal.
        await _seed_catalogs(db, clinic_id=clinic.id, actor_id=admin.id)

        patients = await _seed_patients(db, clinic_id=clinic.id, actor_id=admin.id)
        await _seed_clinical_records(
            db, clinic_id=clinic.id, professional_id=odontologo.id, patients=patients
        )
        provider, resource = await _seed_agenda(
            db,
            clinic_id=clinic.id,
            admin_id=admin.id,
            odontologo_id=odontologo.id,
            patients=patients,
        )
        # _seed_treatment va antes: crea el catalogo de procedimientos (tabla
        # procedure_catalog) que _seed_example_patient necesita para su propio plan
        # de tratamiento de muestra.
        await _seed_treatment(
            db,
            clinic_id=clinic.id,
            admin_id=admin.id,
            professional_id=odontologo.id,
            patients=patients,
        )
        await _seed_example_patient(
            db,
            clinic_id=clinic.id,
            admin_id=admin.id,
            professional_id=odontologo.id,
            provider_id=provider.id,
            resource_id=resource.id,
        )
        await _seed_document_templates(db, clinic_id=clinic.id, actor_id=admin.id)

        print(f"Organizacion: {organization.name}")
        print(f"Sucursal: {clinic.name}")
        print(f"Admin: {ADMIN_EMAIL} / {DEMO_PASSWORD} (debe configurar MFA al entrar)")
        print(f"Odontologo: {ODONTOLOGO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Recepcion: {RECEPCION_EMAIL} / {DEMO_PASSWORD}")
        print(f"Caja: {CAJA_EMAIL} / {DEMO_PASSWORD}")
        print(f"Pacientes ficticios creados: {PATIENT_COUNT}")
        print(
            "Expediente de muestra (Fase 4) en 3 de los pacientes sembrados (alertas, nota SOAP)."
        )
        print(
            "Odontograma de muestra (Fase 5): caries tratada con resina en 36-O "
            "(historial), caries activa en 36-D y 46-O, pieza 18 ausente."
        )
        print(
            "Agenda de muestra (Fase 6): 1 profesional, 1 gabinete, horario laboral "
            "abierto toda la semana, una cita reservada manana, una confirmada "
            "manana y una en 7 dias."
        )
        print(
            "Paciente de ejemplo con expediente completo: Roberto Fernandez Castillo "
            "-- 3 consultas (endodoncia y corona en pieza 16, caries y sellador en "
            "otras piezas), alergia/medicamento/signos vitales, un plan de "
            "tratamiento ya TERMINADO, 2 citas pasadas (una TERMINADA, una NO_SHOW) "
            "y 2 citas futuras: proximo lunes 9:00 y proximo martes 11:00."
        )
        print(
            "Plan de tratamiento de muestra (Fase 7): catalogo de 5 procedimientos, "
            "1 diagnostico, plan de 2 fases en la pieza 46 (fase 1 aceptada y "
            "realizada -- con cargo sugerido --, fase 2 solo planificada)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
