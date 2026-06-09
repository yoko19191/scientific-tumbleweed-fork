"""DTOs for the academic data search workspace app."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AcademicDataSearchStatusResponse(BaseModel):
    """Configuration status for the academic data search service."""

    status: Literal["available", "not_configured"] = Field(..., description="Service status")
    configured: bool = Field(..., description="Whether backend credentials are configured")
    message: str = Field(..., description="User-facing status message")
    capabilities: list[str] = Field(default_factory=list, description="Available search flows")


class AcademicDataSearchErrorDetail(BaseModel):
    """Stable error detail returned by the Gateway."""

    code: str = Field(..., description="Stable application error code")
    message: str = Field(..., description="User-facing error message")


class SearchMeta(BaseModel):
    """Search pagination metadata."""

    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1)
    total: int | None = None


class AcademicLinks(BaseModel):
    """Normalized public links for one academic record."""

    primary_url: str | None = None
    pdf_url: str | None = None


class PaperSearchRequest(BaseModel):
    """Paper search criteria."""

    query: str = Field(..., min_length=1, max_length=200)
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(10, ge=1, le=50)


class PaperRecommendationRequest(BaseModel):
    """Paper recommendation criteria."""

    scholar: str = Field("", max_length=120)
    organization: str = Field("", max_length=160)
    topic: str = Field("", max_length=200)
    year_start: int | None = Field(default=None, ge=1800, le=2200)
    year_end: int | None = Field(default=None, ge=1800, le=2200)
    language: Literal["any", "zh", "en"] = "any"
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_recommendation_signal(self) -> PaperRecommendationRequest:
        """Require at least one recommendation signal and a sane year range."""
        if self.year_start is not None and self.year_end is not None and self.year_start > self.year_end:
            raise ValueError("year_start must be less than or equal to year_end")
        if not any(value.strip() for value in (self.scholar, self.organization, self.topic)):
            raise ValueError("Provide at least one scholar, organization, or topic")
        return self


class PaperSummary(BaseModel):
    """Normalized paper summary."""

    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    citation_count: int | None = None
    citation_bucket: str | None = None
    doi: str | None = None
    abstract: str | None = None
    links: AcademicLinks = Field(default_factory=AcademicLinks)


class PaperDetail(PaperSummary):
    """Normalized paper detail."""

    keywords: list[str] = Field(default_factory=list)


class PaperSearchResponse(BaseModel):
    """Paper search response."""

    meta: SearchMeta
    items: list[PaperSummary]


class PaperRecommendationResponse(BaseModel):
    """Paper recommendation response."""

    meta: SearchMeta
    items: list[PaperSummary]


class PatentSearchRequest(BaseModel):
    """Patent search criteria."""

    query: str = Field(..., min_length=1, max_length=200)
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(10, ge=1, le=50)


class PatentSummary(BaseModel):
    """Normalized patent summary."""

    id: str
    title: str
    publication_year: int | None = None
    application_year: int | None = None
    first_inventor: str | None = None
    applicant: str | None = None


class PatentDetail(PatentSummary):
    """Normalized patent detail."""

    abstract: str | None = None
    inventors: list[str] = Field(default_factory=list)
    applicants: list[str] = Field(default_factory=list)
    publication_number: str | None = None
    application_number: str | None = None


class PatentSearchResponse(BaseModel):
    """Patent search response."""

    meta: SearchMeta
    items: list[PatentSummary]


class OrganizationSearchRequest(BaseModel):
    """Organization search criteria."""

    query: str = Field(..., min_length=1, max_length=160)
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(10, ge=1, le=50)


class OrganizationSummary(BaseModel):
    """Normalized organization summary."""

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    total_count: int | None = None


class OrganizationSearchResponse(BaseModel):
    """Organization search response."""

    meta: SearchMeta
    items: list[OrganizationSummary]


class VenueSearchRequest(BaseModel):
    """Venue search criteria."""

    query: str = Field(..., min_length=1, max_length=160)
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(10, ge=1, le=50)


class VenueSummary(BaseModel):
    """Normalized venue summary."""

    id: str
    english_name: str
    chinese_name: str | None = None
    venue_type: str | None = None
    aliases: list[str] = Field(default_factory=list)


class VenueSearchResponse(BaseModel):
    """Venue search response."""

    meta: SearchMeta
    items: list[VenueSummary]
