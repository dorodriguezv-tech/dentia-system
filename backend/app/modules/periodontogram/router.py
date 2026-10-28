import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User
from app.modules.periodontogram import rules, service
from app.modules.periodontogram.models import PeriodontalProbingSite
from app.modules.periodontogram.schemas import (
    AnnulRequest,
    IndexType,
    IndicesSummaryOut,
    OcclusalContactEntryCreateRequest,
    OcclusalContactEntryOut,
    PeriodontalIndexEntryCreateRequest,
    PeriodontalIndexEntryOut,
    PeriodontalProbingSiteCreateRequest,
    PeriodontalProbingSiteOut,
    PeriodontalToothMeasurementCreateRequest,
    PeriodontalToothMeasurementOut,
    PeriodontogramObservationCreateRequest,
    PeriodontogramObservationOut,
)

router = APIRouter(tags=["periodontogram"])

_BASE = "/patients/{patient_id}/periodontogram"


def _to_probing_site_out(item: PeriodontalProbingSite) -> PeriodontalProbingSiteOut:
    # El nivel de inserccion clinica (CAL) nunca se persiste -- se calcula al
    # vuelo aqui, mismo criterio que el IMC de la Fase A (records/router.py).
    out = PeriodontalProbingSiteOut.model_validate(item)
    out.clinical_attachment_level_mm = rules.clinical_attachment_level_mm(
        item.probing_depth_mm, item.recession_mm
    )
    return out


# --------------------------------------------------------------------------------
# 1. Sondeo periodontal -- 6 sitios por pieza.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/probing-sites", response_model=list[PeriodontalProbingSiteOut])
async def list_probing_sites(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PeriodontalProbingSiteOut]:
    items = await service.list_probing_sites(db, clinic_id=clinic_id, patient_id=patient_id)
    return [_to_probing_site_out(i) for i in items]


@router.post(f"{_BASE}/probing-sites", response_model=PeriodontalProbingSiteOut, status_code=201)
async def create_probing_site(
    patient_id: uuid.UUID,
    payload: PeriodontalProbingSiteCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalProbingSiteOut:
    item = await service.create_probing_site(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return _to_probing_site_out(item)


@router.post(f"{_BASE}/probing-sites/{{item_id}}/annul", response_model=PeriodontalProbingSiteOut)
async def annul_probing_site(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalProbingSiteOut:
    item = await service.annul_probing_site(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return _to_probing_site_out(item)


# --------------------------------------------------------------------------------
# 2. Medicion por pieza -- movilidad y furcacion.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/tooth-measurements", response_model=list[PeriodontalToothMeasurementOut])
async def list_tooth_measurements(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PeriodontalToothMeasurementOut]:
    items = await service.list_tooth_measurements(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PeriodontalToothMeasurementOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/tooth-measurements", response_model=PeriodontalToothMeasurementOut, status_code=201
)
async def create_tooth_measurement(
    patient_id: uuid.UUID,
    payload: PeriodontalToothMeasurementCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalToothMeasurementOut:
    item = await service.create_tooth_measurement(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PeriodontalToothMeasurementOut.model_validate(item)


@router.post(
    f"{_BASE}/tooth-measurements/{{item_id}}/annul", response_model=PeriodontalToothMeasurementOut
)
async def annul_tooth_measurement(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalToothMeasurementOut:
    item = await service.annul_tooth_measurement(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PeriodontalToothMeasurementOut.model_validate(item)


# --------------------------------------------------------------------------------
# 3. Indices de placa dentobacteriana y gingival.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/index-entries", response_model=list[PeriodontalIndexEntryOut])
async def list_index_entries(
    patient_id: uuid.UUID,
    index_type: IndexType | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PeriodontalIndexEntryOut]:
    items = await service.list_index_entries(
        db, clinic_id=clinic_id, patient_id=patient_id, index_type=index_type
    )
    return [PeriodontalIndexEntryOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/index-entries", response_model=PeriodontalIndexEntryOut, status_code=201)
async def create_index_entry(
    patient_id: uuid.UUID,
    payload: PeriodontalIndexEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalIndexEntryOut:
    item = await service.create_index_entry(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PeriodontalIndexEntryOut.model_validate(item)


@router.post(f"{_BASE}/index-entries/{{item_id}}/annul", response_model=PeriodontalIndexEntryOut)
async def annul_index_entry(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontalIndexEntryOut:
    item = await service.annul_index_entry(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PeriodontalIndexEntryOut.model_validate(item)


@router.get(f"{_BASE}/indices-summary", response_model=IndicesSummaryOut)
async def get_indices_summary(
    patient_id: uuid.UUID,
    encounter_id: uuid.UUID | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> IndicesSummaryOut:
    return await service.get_indices_summary(
        db, clinic_id=clinic_id, patient_id=patient_id, encounter_id=encounter_id
    )


# --------------------------------------------------------------------------------
# 4. Tablas de oclusion -- contactos marcados.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/occlusal-contacts", response_model=list[OcclusalContactEntryOut])
async def list_occlusal_contacts(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[OcclusalContactEntryOut]:
    items = await service.list_occlusal_contacts(db, clinic_id=clinic_id, patient_id=patient_id)
    return [OcclusalContactEntryOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/occlusal-contacts", response_model=OcclusalContactEntryOut, status_code=201)
async def create_occlusal_contact(
    patient_id: uuid.UUID,
    payload: OcclusalContactEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OcclusalContactEntryOut:
    item = await service.create_occlusal_contact(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return OcclusalContactEntryOut.model_validate(item)


@router.post(f"{_BASE}/occlusal-contacts/{{item_id}}/annul", response_model=OcclusalContactEntryOut)
async def annul_occlusal_contact(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> OcclusalContactEntryOut:
    item = await service.annul_occlusal_contact(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return OcclusalContactEntryOut.model_validate(item)


# --------------------------------------------------------------------------------
# 5. Observaciones del periodontograma.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/observations", response_model=list[PeriodontogramObservationOut])
async def list_observations(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PeriodontogramObservationOut]:
    items = await service.list_observations(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PeriodontogramObservationOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/observations", response_model=PeriodontogramObservationOut, status_code=201)
async def create_observation(
    patient_id: uuid.UUID,
    payload: PeriodontogramObservationCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontogramObservationOut:
    item = await service.create_observation(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PeriodontogramObservationOut.model_validate(item)


@router.post(f"{_BASE}/observations/{{item_id}}/annul", response_model=PeriodontogramObservationOut)
async def annul_observation(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PeriodontogramObservationOut:
    item = await service.annul_observation(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PeriodontogramObservationOut.model_validate(item)


# --------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/pdf")
async def get_periodontogram_pdf(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_periodontogram_pdf(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    filename = f"periodontograma-{patient_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
