import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.endodontic_history import service
from app.modules.endodontic_history.schemas import (
    AnnulRequest,
    EndodonticDiagnosisTreatmentCreateRequest,
    EndodonticDiagnosisTreatmentOut,
    EndodonticInterrogationCreateRequest,
    EndodonticInterrogationOut,
    EndodonticPeriodontalTestCreateRequest,
    EndodonticPeriodontalTestOut,
    EndodonticPulpSensitivityTestCreateRequest,
    EndodonticPulpSensitivityTestOut,
    EndodonticRadiographicInterpretationCreateRequest,
    EndodonticRadiographicInterpretationOut,
    EndodonticToothDiagnosisCodeCreateRequest,
    EndodonticToothDiagnosisCodeOut,
    EndodonticToothKind,
    EndodonticWorkingLengthCreateRequest,
    EndodonticWorkingLengthOut,
)
from app.modules.iam.models import User

router = APIRouter(tags=["endodontic_history"])

_BASE = "/patients/{patient_id}/endodontic-history"


# --------------------------------------------------------------------------------
# 1. Interrogatorio + examen intrabucal/extrabucal.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/interrogation", response_model=list[EndodonticInterrogationOut])
async def list_interrogations(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticInterrogationOut]:
    items = await service.list_interrogations(db, clinic_id=clinic_id, patient_id=patient_id)
    return [EndodonticInterrogationOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/interrogation", response_model=EndodonticInterrogationOut, status_code=201)
async def create_interrogation(
    patient_id: uuid.UUID,
    payload: EndodonticInterrogationCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticInterrogationOut:
    item = await service.create_interrogation(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticInterrogationOut.model_validate(item)


@router.post(f"{_BASE}/interrogation/{{item_id}}/annul", response_model=EndodonticInterrogationOut)
async def annul_interrogation(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticInterrogationOut:
    item = await service.annul_interrogation(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticInterrogationOut.model_validate(item)


# --------------------------------------------------------------------------------
# 2. Pruebas de sensibilidad pulpar.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/pulp-sensitivity-test", response_model=list[EndodonticPulpSensitivityTestOut])
async def list_pulp_sensitivity_tests(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticPulpSensitivityTestOut]:
    items = await service.list_pulp_sensitivity_tests(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [EndodonticPulpSensitivityTestOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/pulp-sensitivity-test",
    response_model=EndodonticPulpSensitivityTestOut,
    status_code=201,
)
async def create_pulp_sensitivity_test(
    patient_id: uuid.UUID,
    payload: EndodonticPulpSensitivityTestCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticPulpSensitivityTestOut:
    item = await service.create_pulp_sensitivity_test(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticPulpSensitivityTestOut.model_validate(item)


@router.post(
    f"{_BASE}/pulp-sensitivity-test/{{item_id}}/annul",
    response_model=EndodonticPulpSensitivityTestOut,
)
async def annul_pulp_sensitivity_test(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticPulpSensitivityTestOut:
    item = await service.annul_pulp_sensitivity_test(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticPulpSensitivityTestOut.model_validate(item)


# --------------------------------------------------------------------------------
# 3. Pruebas periodontales.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/periodontal-test", response_model=list[EndodonticPeriodontalTestOut])
async def list_periodontal_tests(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticPeriodontalTestOut]:
    items = await service.list_periodontal_tests(db, clinic_id=clinic_id, patient_id=patient_id)
    return [EndodonticPeriodontalTestOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/periodontal-test", response_model=EndodonticPeriodontalTestOut, status_code=201
)
async def create_periodontal_test(
    patient_id: uuid.UUID,
    payload: EndodonticPeriodontalTestCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticPeriodontalTestOut:
    item = await service.create_periodontal_test(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticPeriodontalTestOut.model_validate(item)


@router.post(
    f"{_BASE}/periodontal-test/{{item_id}}/annul", response_model=EndodonticPeriodontalTestOut
)
async def annul_periodontal_test(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticPeriodontalTestOut:
    item = await service.annul_periodontal_test(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticPeriodontalTestOut.model_validate(item)


# --------------------------------------------------------------------------------
# 4. Interpretacion radiografica.
# --------------------------------------------------------------------------------


@router.get(
    f"{_BASE}/radiographic-interpretation",
    response_model=list[EndodonticRadiographicInterpretationOut],
)
async def list_radiographic_interpretations(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticRadiographicInterpretationOut]:
    items = await service.list_radiographic_interpretations(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [EndodonticRadiographicInterpretationOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/radiographic-interpretation",
    response_model=EndodonticRadiographicInterpretationOut,
    status_code=201,
)
async def create_radiographic_interpretation(
    patient_id: uuid.UUID,
    payload: EndodonticRadiographicInterpretationCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticRadiographicInterpretationOut:
    item = await service.create_radiographic_interpretation(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticRadiographicInterpretationOut.model_validate(item)


@router.post(
    f"{_BASE}/radiographic-interpretation/{{item_id}}/annul",
    response_model=EndodonticRadiographicInterpretationOut,
)
async def annul_radiographic_interpretation(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticRadiographicInterpretationOut:
    item = await service.annul_radiographic_interpretation(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticRadiographicInterpretationOut.model_validate(item)


# --------------------------------------------------------------------------------
# 5. Diagnostico y tratamiento.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/diagnosis-treatment", response_model=list[EndodonticDiagnosisTreatmentOut])
async def list_diagnosis_treatments(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticDiagnosisTreatmentOut]:
    items = await service.list_diagnosis_treatments(db, clinic_id=clinic_id, patient_id=patient_id)
    return [EndodonticDiagnosisTreatmentOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/diagnosis-treatment", response_model=EndodonticDiagnosisTreatmentOut, status_code=201
)
async def create_diagnosis_treatment(
    patient_id: uuid.UUID,
    payload: EndodonticDiagnosisTreatmentCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticDiagnosisTreatmentOut:
    item = await service.create_diagnosis_treatment(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticDiagnosisTreatmentOut.model_validate(item)


@router.post(
    f"{_BASE}/diagnosis-treatment/{{item_id}}/annul",
    response_model=EndodonticDiagnosisTreatmentOut,
)
async def annul_diagnosis_treatment(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticDiagnosisTreatmentOut:
    item = await service.annul_diagnosis_treatment(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticDiagnosisTreatmentOut.model_validate(item)


# --------------------------------------------------------------------------------
# 6. Odontograma de diagnostico/evolucion -- 18 codigos por pieza.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/tooth-diagnosis-code", response_model=list[EndodonticToothDiagnosisCodeOut])
async def list_tooth_diagnosis_codes(
    patient_id: uuid.UUID,
    kind: EndodonticToothKind | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticToothDiagnosisCodeOut]:
    items = await service.list_tooth_diagnosis_codes(
        db, clinic_id=clinic_id, patient_id=patient_id, kind=kind
    )
    return [EndodonticToothDiagnosisCodeOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/tooth-diagnosis-code",
    response_model=EndodonticToothDiagnosisCodeOut,
    status_code=201,
)
async def create_tooth_diagnosis_code(
    patient_id: uuid.UUID,
    payload: EndodonticToothDiagnosisCodeCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticToothDiagnosisCodeOut:
    item = await service.create_tooth_diagnosis_code(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticToothDiagnosisCodeOut.model_validate(item)


@router.post(
    f"{_BASE}/tooth-diagnosis-code/{{item_id}}/annul",
    response_model=EndodonticToothDiagnosisCodeOut,
)
async def annul_tooth_diagnosis_code(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticToothDiagnosisCodeOut:
    item = await service.annul_tooth_diagnosis_code(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticToothDiagnosisCodeOut.model_validate(item)


# --------------------------------------------------------------------------------
# 7. Longitud de trabajo + datos de tratamiento.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/working-length", response_model=list[EndodonticWorkingLengthOut])
async def list_working_lengths(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EndodonticWorkingLengthOut]:
    items = await service.list_working_lengths(db, clinic_id=clinic_id, patient_id=patient_id)
    return [EndodonticWorkingLengthOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/working-length", response_model=EndodonticWorkingLengthOut, status_code=201)
async def create_working_length(
    patient_id: uuid.UUID,
    payload: EndodonticWorkingLengthCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticWorkingLengthOut:
    item = await service.create_working_length(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return EndodonticWorkingLengthOut.model_validate(item)


@router.post(f"{_BASE}/working-length/{{item_id}}/annul", response_model=EndodonticWorkingLengthOut)
async def annul_working_length(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EndodonticWorkingLengthOut:
    item = await service.annul_working_length(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return EndodonticWorkingLengthOut.model_validate(item)


# --------------------------------------------------------------------------------
# PDF.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/pdf")
async def get_endodontic_history_pdf(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_endodontic_history_pdf(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    filename = f"historia-clinica-endodoncia-{patient_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
