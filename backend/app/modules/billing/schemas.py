import uuid
from decimal import Decimal

from pydantic import BaseModel


class ChargeOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    procedure_performed_id: uuid.UUID
    amount: Decimal
    status: str
    description: str | None

    model_config = {"from_attributes": True}
