from pydantic import BaseModel, Field


class DocumentSettingsOut(BaseModel):
    institutional_title: str | None
    place_label: str | None
    logo_left_url: str | None
    logo_right_url: str | None
    has_logo_left: bool
    has_logo_right: bool


class DocumentSettingsUpdateRequest(BaseModel):
    institutional_title: str | None = Field(default=None, max_length=300)
    place_label: str | None = Field(default=None, max_length=150)
