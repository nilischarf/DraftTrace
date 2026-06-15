from typing import List, Literal

from pydantic import BaseModel, Field


class SubmissionRequest(BaseModel):
    document_url: str = Field(..., min_length=1)
    student_name: str = Field(..., min_length=1)
    assignment_name: str = Field(..., min_length=1)


class SnapshotProbeRequest(BaseModel):
    document_url: str = Field(..., min_length=1)
    max_revisions: int = Field(default=8, ge=1, le=20)


class TimelineEvent(BaseModel):
    time: str
    label: str
    detail: str
    severity: Literal["low", "medium", "high"]


class AuthorshipReport(BaseModel):
    id: str
    student_name: str
    assignment_name: str
    document_url: str
    status: Literal["low_concern", "needs_review", "insufficient_evidence"]
    confidence_score: int
    summary: str
    metrics: dict
    timeline: List[TimelineEvent]
    teacher_note: str
