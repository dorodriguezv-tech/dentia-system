"""Datos ficticios de arranque (CLAUDE.md sec. 5: nunca datos reales de pacientes).

Uso: python -m app.seed
Crea una organizacion y una sucursal de ejemplo, un admin_clinica (con MFA
pendiente de configurar, ver regla de CLAUDE.md sec. 5) y un odontologo.
Es idempotente: si el admin ya existe, no hace nada.
"""

import asyncio
import random
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.agenda import service as agenda_service
from app.modules.agenda.schemas import (
    AppointmentCreateRequest,
    ProviderCreateRequest,
    ResourceCreateRequest,
    StatusChangeRequest,
    WorkingHoursCreateRequest,
)
from app.modules.diagnosis import service as diagnosis_service
from app.modules.diagnosis.schemas import DiagnosisCreateRequest
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
from app.modules.patients import service as patients_service
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientCreateRequest
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

ADMIN_EMAIL = "admin@dentalcare-demo.mx"
ODONTOLOGO_EMAIL = "odontologo@dentalcare-demo.mx"
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
) -> None:
    """Agenda de muestra (Fase 6): un profesional agendable, un gabinete, horario
    laboral de lunes a viernes y citas en distintos estados para ver el calendario
    poblado (reservada, confirmada y una en la semana siguiente)."""
    provider, _name = await agenda_service.create_provider(
        db,
        clinic_id=clinic_id,
        data=ProviderCreateRequest(user_id=odontologo_id, color="#2BB3A3"),
        actor_id=admin_id,
    )
    resource = await agenda_service.create_resource(
        db, clinic_id=clinic_id, data=ResourceCreateRequest(name="Gabinete 1"), actor_id=admin_id
    )

    for weekday in range(5):  # lunes (0) a viernes (4)
        await agenda_service.create_working_hours(
            db,
            clinic_id=clinic_id,
            provider_id=provider.id,
            data=WorkingHoursCreateRequest(
                weekday=weekday, start_time=time(9, 0), end_time=time(14, 0)
            ),
        )
        await agenda_service.create_working_hours(
            db,
            clinic_id=clinic_id,
            provider_id=provider.id,
            data=WorkingHoursCreateRequest(
                weekday=weekday, start_time=time(16, 0), end_time=time(20, 0)
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

        admin = User(
            email=ADMIN_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        odontologo = User(
            email=ODONTOLOGO_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add_all([admin, odontologo])
        await db.flush()

        db.add_all(
            [
                UserClinic(user_id=admin.id, clinic_id=clinic.id, role_id=admin_role.id),
                UserClinic(user_id=odontologo.id, clinic_id=clinic.id, role_id=odontologo_role.id),
            ]
        )
        await db.commit()

        patients = await _seed_patients(db, clinic_id=clinic.id, actor_id=admin.id)
        await _seed_clinical_records(
            db, clinic_id=clinic.id, professional_id=odontologo.id, patients=patients
        )
        await _seed_agenda(
            db,
            clinic_id=clinic.id,
            admin_id=admin.id,
            odontologo_id=odontologo.id,
            patients=patients,
        )
        await _seed_treatment(
            db,
            clinic_id=clinic.id,
            admin_id=admin.id,
            professional_id=odontologo.id,
            patients=patients,
        )

        print(f"Organizacion: {organization.name}")
        print(f"Sucursal: {clinic.name}")
        print(f"Admin: {ADMIN_EMAIL} / {DEMO_PASSWORD} (debe configurar MFA al entrar)")
        print(f"Odontologo: {ODONTOLOGO_EMAIL} / {DEMO_PASSWORD}")
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
            "L-V, una cita reservada manana, una confirmada manana y una en 7 dias."
        )
        print(
            "Plan de tratamiento de muestra (Fase 7): catalogo de 5 procedimientos, "
            "1 diagnostico, plan de 2 fases en la pieza 46 (fase 1 aceptada y "
            "realizada -- con cargo sugerido --, fase 2 solo planificada)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
