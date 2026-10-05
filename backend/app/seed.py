"""Datos ficticios de arranque (CLAUDE.md sec. 5: nunca datos reales de pacientes).

Uso: python -m app.seed
Crea una organizacion y una sucursal de ejemplo, un admin_clinica (con MFA
pendiente de configurar, ver regla de CLAUDE.md sec. 5) y un odontologo.
Es idempotente: si el admin ya existe, no hace nada.
"""

import asyncio
import random
import uuid

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.encounters import service as encounters_service
from app.modules.encounters.schemas import (
    ClinicalNoteCreateRequest,
    CorrectNoteRequest,
    EncounterCreateRequest,
    FinalizeNoteRequest,
)
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic
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

        print(f"Organizacion: {organization.name}")
        print(f"Sucursal: {clinic.name}")
        print(f"Admin: {ADMIN_EMAIL} / {DEMO_PASSWORD} (debe configurar MFA al entrar)")
        print(f"Odontologo: {ODONTOLOGO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Pacientes ficticios creados: {PATIENT_COUNT}")
        print(
            "Expediente de muestra (Fase 4) en 3 de los pacientes sembrados (alertas, nota SOAP)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
