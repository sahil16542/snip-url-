from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


RESERVED_ALIASES = frozenset({"health", "docs", "openapi.json", "shorten", "redoc"})


class URLCreateRequest(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=16,
        pattern=r"^[A-Za-z0-9]+$",
    )

    @field_validator("custom_alias")
    @classmethod
    def _reject_reserved(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() in RESERVED_ALIASES:
            raise ValueError("alias is reserved")
        return v


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
