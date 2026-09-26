import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

_HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class Author(BaseModel):
    name: str
    link: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("author.name must not be blank")
        return v

    @field_validator("link")
    @classmethod
    def link_must_be_http(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _HTTP_URL_RE.match(v):
            raise ValueError("author.link must start with http:// or https://")
        return v


class Media(BaseModel):
    image: str
    caption: Optional[str] = None


class QuoteFile(BaseModel):
    id: str
    added: str
    date: str
    original_language: str
    translations: dict[str, str]
    author: Author
    media: Optional[Media] = None

    @field_validator("added")
    @classmethod
    def added_is_iso_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("added must be an ISO date, YYYY-MM-DD") from exc
        return v

    @field_validator("translations")
    @classmethod
    def translations_not_empty(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("translations must not be empty")
        for lang, text in v.items():
            if not text.strip():
                raise ValueError(f"translation for '{lang}' must not be blank")
        return v

    @model_validator(mode="after")
    def original_language_has_translation(self) -> "QuoteFile":
        if self.original_language not in self.translations:
            raise ValueError(
                "original_language must have a matching entry in translations"
            )
        return self

    def filename_prefix(self) -> str:
        return self.added.replace("-", "")
