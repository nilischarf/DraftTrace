from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from app.models import AuthorshipReport, SubmissionRequest, TimelineEvent


def create_mock_report(
    submission: SubmissionRequest,
    google_document: Optional[Dict] = None,
) -> AuthorshipReport:
    """Return a realistic placeholder report until Google Docs data is connected."""
    if google_document:
        return _create_google_metadata_report(submission, google_document)

    return AuthorshipReport(
        id=str(uuid4()),
        student_name=submission.student_name,
        assignment_name=submission.assignment_name,
        document_url=submission.document_url,
        status="needs_review",
        confidence_score=68,
        summary=(
            "This draft shows one large late-stage insertion and a short visible "
            "drafting window. This does not prove AI use, but it is enough to "
            "recommend teacher review."
        ),
        metrics={
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "visible_drafting_window": "22 minutes",
            "revision_count": 6,
            "final_word_count": 1480,
            "largest_single_insertion": "1,120 words",
            "collaborators": 1,
        },
        timeline=[
            TimelineEvent(
                time="09:12",
                label="Document created",
                detail="The document was created shortly before final submission.",
                severity="medium",
            ),
            TimelineEvent(
                time="09:18",
                label="Small edits",
                detail="Title and opening sentence were added in several short edits.",
                severity="low",
            ),
            TimelineEvent(
                time="09:29",
                label="Large insertion",
                detail="Approximately 1,120 words appeared in a single revision.",
                severity="high",
            ),
            TimelineEvent(
                time="09:34",
                label="Final polish",
                detail="A few punctuation and formatting edits were made before submission.",
                severity="low",
            ),
        ],
        teacher_note=(
            "Ask the student where they drafted the essay and whether any outside "
            "tools were used. Treat this as a conversation starter, not a verdict."
        ),
    )


def _create_google_metadata_report(
    submission: SubmissionRequest,
    google_document: Dict,
) -> AuthorshipReport:
    file_metadata = google_document["file"]
    revisions = google_document["revisions"]
    revision_count = len(revisions)
    created_time = file_metadata.get("createdTime", "Unknown")
    modified_time = file_metadata.get("modifiedTime", "Unknown")
    owner = _person_name(file_metadata.get("owners", [{}])[0])
    last_modifier = _person_name(file_metadata.get("lastModifyingUser", {}))

    return AuthorshipReport(
        id=str(uuid4()),
        student_name=submission.student_name,
        assignment_name=submission.assignment_name,
        document_url=file_metadata.get("webViewLink", submission.document_url),
        status="insufficient_evidence" if revision_count < 2 else "needs_review",
        confidence_score=35 if revision_count < 2 else 52,
        summary=(
            "Google Drive metadata was retrieved successfully. This first real-data "
            "report confirms document access and revision visibility; deeper writing "
            "pattern analysis comes next."
        ),
        metrics={
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "document_title": file_metadata.get("name", "Untitled document"),
            "revision_count": revision_count,
            "created_time": created_time,
            "modified_time": modified_time,
            "owner": owner,
            "last_modifier": last_modifier,
        },
        timeline=_revision_timeline(revisions, created_time),
        teacher_note=(
            "This report currently verifies Google access and revision metadata. "
            "It is not yet making an authorship judgment from text changes."
        ),
    )


def _revision_timeline(revisions: list, created_time: str) -> list:
    if not revisions:
        return [
            TimelineEvent(
                time=_short_time(created_time),
                label="Document metadata found",
                detail="Drive returned document metadata, but no revisions were visible.",
                severity="medium",
            )
        ]

    recent_revisions = revisions[-5:]
    return [
        TimelineEvent(
            time=_short_time(revision.get("modifiedTime", "")),
            label=f"Revision {revision.get('id', 'unknown')}",
            detail=f"Last modified by {_person_name(revision.get('lastModifyingUser', {}))}.",
            severity="low",
        )
        for revision in recent_revisions
    ]


def _person_name(person: Dict) -> str:
    return person.get("displayName") or person.get("emailAddress") or "Unknown"


def _short_time(timestamp: str) -> str:
    if "T" not in timestamp:
        return "Unknown"

    return timestamp.split("T", 1)[1][:5]
