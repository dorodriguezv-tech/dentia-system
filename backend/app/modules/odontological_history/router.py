import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User
from app.modules.odontological_history import service
from app.modules.odontological_history.schemas import (
    AnnulRequest,
    OdontogramDiagnosisDetailCreateRequest,
    OdontogramDiagnosisDetailOut,
    OdontologicalExamCreateRequest,
    OdontologicalExamOut,
    ParallelometerAnalysisCreateRequest,
    ParallelometerAnalysisOut,
    PeriodontalAnamnesisCreateRequest,
    PeriodontalAnamnesisOut,
    RadiographicAnalysisCreateRequest,
    RadiographicAnalysisOut,
    RemovablePartialDentureDesignCreateRequest,
    RemovablePartialDentureDesignOut,
    ToothDiagnosisEntryCreateRequest,
    ToothDiagnosisEntryOut,
    ToothTreatmentPlanEntryCreateRequest,
    ToothTreatmentPlanEntryOut,
)

router = APIRouter(tags=["odontological_history"])

_BASE = "/patients/{patient_id}/odontological-history"


# --------------------------------------------------------------------------------
# 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/exam", response_model=list[OdontologicalExamOut])
async def list_odontological_exams(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[OdontologicalExamOut]:
    items = await service.list_odontological_exams(db, clinic_id=clinic_id, patient_id=patient_id)
    return [OdontologicalExamOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/exam", response_model=OdontologicalExamOut, status_code=201)
async def create_odontological_exam(
    patient_id: uuid.UUID,
    payload: OdontologicalExamCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OdontologicalExamOut:
    item = await service.create_odontological_exam(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return OdontologicalExamOut.model_validate(item)


@router.post(f"{_BASE}/exam/{{item_id}}/annul", response_model=OdontologicalExamOut)
async def annul_odontological_exam(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OdontologicalExamOut:
    item = await service.annul_odontological_exam(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return OdontologicalExamOut.model_validate(item)


# --------------------------------------------------------------------------------
# 2. Anamnesis periodontal.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/periodontal-anamnesis", response_model=list[PeriodontalAnamnesisOut])
async def list_periodontal_anamneses(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PeriodontalAnamnesisOut]:
    items = await service.list_periodontal_anamneses(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PeriodontalAnamnesisOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/periodontal-anamnesis", response_model=PeriodontalAnamnesisOut, status_code=201
)
async def create_periodontal_anamnesis(
    patient_id: uuid.UUID,
    payload: PeriodontalAnamnesisCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalAnamnesisOut:
    item = await service.create_periodontal_anamnesis(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PeriodontalAnamnesisOut.model_validate(item)


@router.post(
    f"{_BASE}/periodontal-anamnesis/{{item_id}}/annul", response_model=PeriodontalAnamnesisOut
)
async def annul_periodontal_anamnesis(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalAnamnesisOut:
    item = await service.annul_periodontal_anamnesis(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PeriodontalAnamnesisOut.model_validate(item)


# --------------------------------------------------------------------------------
# 3. Auxiliares de diagnostico -- analisis radiografico.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/radiographic-analysis", response_model=list[RadiographicAnalysisOut])
async def list_radiographic_analyses(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[RadiographicAnalysisOut]:
    items = await service.list_radiographic_analyses(db, clinic_id=clinic_id, patient_id=patient_id)
    return [RadiographicAnalysisOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/radiographic-analysis", response_model=RadiographicAnalysisOut, status_code=201
)
async def create_radiographic_analysis(
    patient_id: uuid.UUID,
    payload: RadiographicAnalysisCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> RadiographicAnalysisOut:
    item = await service.create_radiographic_analysis(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return RadiographicAnalysisOut.model_validate(item)


@router.post(
    f"{_BASE}/radiographic-analysis/{{item_id}}/annul", response_model=RadiographicAnalysisOut
)
async def annul_radiographic_analysis(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> RadiographicAnalysisOut:
    item = await service.annul_radiographic_analysis(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return RadiographicAnalysisOut.model_validate(item)


# --------------------------------------------------------------------------------
# 4. Odontograma de diagnostico -- datos complementarios.
# --------------------------------------------------------------------------------


@router.get(
    f"{_BASE}/odontogram-diagnosis-detail", response_model=list[OdontogramDiagnosisDetailOut]
)
async def list_odontogram_diagnosis_details(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[OdontogramDiagnosisDetailOut]:
    items = await service.list_odontogram_diagnosis_details(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [OdontogramDiagnosisDetailOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/odontogram-diagnosis-detail",
    response_model=OdontogramDiagnosisDetailOut,
    status_code=201,
)
async def create_odontogram_diagnosis_detail(
    patient_id: uuid.UUID,
    payload: OdontogramDiagnosisDetailCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OdontogramDiagnosisDetailOut:
    item = await service.create_odontogram_diagnosis_detail(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return OdontogramDiagnosisDetailOut.model_validate(item)


@router.post(
    f"{_BASE}/odontogram-diagnosis-detail/{{item_id}}/annul",
    response_model=OdontogramDiagnosisDetailOut,
)
async def annul_odontogram_diagnosis_detail(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OdontogramDiagnosisDetailOut:
    item = await service.annul_odontogram_diagnosis_detail(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return OdontogramDiagnosisDetailOut.model_validate(item)


# --------------------------------------------------------------------------------
# 5. Analisis con paralelometro.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/parallelometer-analysis", response_model=list[ParallelometerAnalysisOut])
async def list_parallelometer_analyses(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ParallelometerAnalysisOut]:
    items = await service.list_parallelometer_analyses(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [ParallelometerAnalysisOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/parallelometer-analysis", response_model=ParallelometerAnalysisOut, status_code=201
)
async def create_parallelometer_analysis(
    patient_id: uuid.UUID,
    payload: ParallelometerAnalysisCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ParallelometerAnalysisOut:
    item = await service.create_parallelometer_analysis(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return ParallelometerAnalysisOut.model_validate(item)


@router.post(
    f"{_BASE}/parallelometer-analysis/{{item_id}}/annul", response_model=ParallelometerAnalysisOut
)
async def annul_parallelometer_analysis(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ParallelometerAnalysisOut:
    item = await service.annul_parallelometer_analysis(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return ParallelometerAnalysisOut.model_validate(item)


# --------------------------------------------------------------------------------
# 6. Diseno de protesis parcial removible.
# --------------------------------------------------------------------------------


@router.get(
    f"{_BASE}/removable-partial-denture-design",
    response_model=list[RemovablePartialDentureDesignOut],
)
async def list_removable_partial_denture_designs(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[RemovablePartialDentureDesignOut]:
    items = await service.list_removable_partial_denture_designs(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [RemovablePartialDentureDesignOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/removable-partial-denture-design",
    response_model=RemovablePartialDentureDesignOut,
    status_code=201,
)
async def create_removable_partial_denture_design(
    patient_id: uuid.UUID,
    payload: RemovablePartialDentureDesignCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> RemovablePartialDentureDesignOut:
    item = await service.create_removable_partial_denture_design(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return RemovablePartialDentureDesignOut.model_validate(item)


@router.post(
    f"{_BASE}/removable-partial-denture-design/{{item_id}}/annul",
    response_model=RemovablePartialDentureDesignOut,
)
async def annul_removable_partial_denture_design(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> RemovablePartialDentureDesignOut:
    item = await service.annul_removable_partial_denture_design(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return RemovablePartialDentureDesignOut.model_validate(item)


# --------------------------------------------------------------------------------
# 7. Diagnostico por organo dental.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/tooth-diagnosis", response_model=list[ToothDiagnosisEntryOut])
async def list_tooth_diagnosis_entries(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ToothDiagnosisEntryOut]:
    items = await service.list_tooth_diagnosis_entries(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [ToothDiagnosisEntryOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/tooth-diagnosis", response_model=ToothDiagnosisEntryOut, status_code=201)
async def create_tooth_diagnosis_entry(
    patient_id: uuid.UUID,
    payload: ToothDiagnosisEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ToothDiagnosisEntryOut:
    item = await service.create_tooth_diagnosis_entry(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return ToothDiagnosisEntryOut.model_validate(item)


@router.post(f"{_BASE}/tooth-diagnosis/{{item_id}}/annul", response_model=ToothDiagnosisEntryOut)
async def annul_tooth_diagnosis_entry(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ToothDiagnosisEntryOut:
    item = await service.annul_tooth_diagnosis_entry(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return ToothDiagnosisEntryOut.model_validate(item)


# --------------------------------------------------------------------------------
# 8. Plan de tratamiento por organo dental.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/tooth-treatment-plan", response_model=list[ToothTreatmentPlanEntryOut])
async def list_tooth_treatment_plan_entries(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ToothTreatmentPlanEntryOut]:
    items = await service.list_tooth_treatment_plan_entries(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [ToothTreatmentPlanEntryOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/tooth-treatment-plan", response_model=ToothTreatmentPlanEntryOut, status_code=201
)
async def create_tooth_treatment_plan_entry(
    patient_id: uuid.UUID,
    payload: ToothTreatmentPlanEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ToothTreatmentPlanEntryOut:
    item = await service.create_tooth_treatment_plan_entry(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return ToothTreatmentPlanEntryOut.model_validate(item)


@router.post(
    f"{_BASE}/tooth-treatment-plan/{{item_id}}/annul", response_model=ToothTreatmentPlanEntryOut
)
async def annul_tooth_treatment_plan_entry(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ToothTreatmentPlanEntryOut:
    item = await service.annul_tooth_treatment_plan_entry(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return ToothTreatmentPlanEntryOut.model_validate(item)


# --------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/pdf")
async def get_odontological_history_pdf(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_odontological_history_pdf(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    filename = f"historia-clinica-odontologica-{patient_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
