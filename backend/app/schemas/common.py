"""Schemas shared by more than one feature."""

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base schema for responses built directly from SQLAlchemy rows."""

    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    """Pagination metadata returned alongside a list payload.

    Attributes:
        page: The current one based page number.
        page_size: The number of items requested per page.
        total: The total number of matching rows.
    """

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class MessageResponse(BaseModel):
    """A simple acknowledgement payload."""

    message: str
