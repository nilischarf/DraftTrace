from datetime import datetime, timezone
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
    analysis = _analyze_revision_metadata(file_metadata, revisions)
    revision_count = analysis["revision_count"]
    created_time = file_metadata.get("createdTime", "Unknown")
    modified_time = file_metadata.get("modifiedTime", "Unknown")
    owner = _person_name(file_metadata.get("owners", [{}])[0])
    last_modifier = _person_name(file_metadata.get("lastModifyingUser", {}))

    return AuthorshipReport(
        id=str(uuid4()),
        student_name=submission.student_name,
        assignment_name=submission.assignment_name,
        document_url=file_metadata.get("webViewLink", submission.document_url),
        status=analysis["status"],
        confidence_score=analysis["confidence_score"],
        summary=analysis["summary"],
        metrics={
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "document_title": file_metadata.get("name", "Untitled document"),
            "revision_count": revision_count,
            "visible_drafting_window": analysis["visible_drafting_window"],
            "first_revision": analysis["first_revision"],
            "last_revision": analysis["last_revision"],
            "unique_editors": analysis["unique_editor_count"],
            "revision_density": analysis["revision_density"],
            "evidence_quality": analysis["evidence_quality"],
            "created_time": created_time,
            "modified_time": modified_time,
            "owner": owner,
            "last_modifier": last_modifier,
        },
        timeline=_analysis_timeline(analysis, revisions, created_time),
        teacher_note=analysis["teacher_note"],
    )


def _analyze_revision_metadata(file_metadata: Dict, revisions: list) -> Dict:
    revision_times = [
        parsed_time
        for parsed_time in (_parse_google_time(revision.get("modifiedTime", "")) for revision in revisions)
        if parsed_time
    ]
    revision_times.sort()

    unique_editors = {
        _person_name(revision.get("lastModifyingUser", {}))
        for revision in revisions
        if _person_name(revision.get("lastModifyingUser", {})) != "Unknown"
    }

    revision_count = len(revisions)
    first_revision = revision_times[0] if revision_times else None
    last_revision = revision_times[-1] if revision_times else None
    window_minutes = _minutes_between(first_revision, last_revision)
    evidence_quality = _evidence_quality(revision_count, window_minutes)
    status, score, summary, teacher_note = _metadata_verdict(
        revision_count=revision_count,
        window_minutes=window_minutes,
        unique_editor_count=len(unique_editors),
        evidence_quality=evidence_quality,
        document_title=file_metadata.get("name", "Untitled document"),
    )

    return {
        "revision_count": revision_count,
        "unique_editor_count": len(unique_editors),
        "visible_drafting_window": _format_duration(window_minutes),
        "first_revision": _format_datetime(first_revision),
        "last_revision": _format_datetime(last_revision),
        "revision_density": _format_revision_density(revision_count, window_minutes),
        "evidence_quality": evidence_quality,
        "status": status,
        "confidence_score": score,
        "summary": summary,
        "teacher_note": teacher_note,
        "window_minutes": window_minutes,
    }


def _metadata_verdict(
    revision_count: int,
    window_minutes: Optional[int],
    unique_editor_count: int,
    evidence_quality: str,
    document_title: str,
) -> tuple:
    if evidence_quality == "Insufficient":
        return (
            "insufficient_evidence",
            28,
            (
                f"DraftTrace could access '{document_title}', but the visible revision "
                "history is too limited to evaluate the writing process."
            ),
            (
                "Ask the student whether they drafted in another tool or copied this "
                "document from another source before submission."
            ),
        )

    concern_points = 0
    reasons = []

    if revision_count <= 3:
        concern_points += 35
        reasons.append("very few visible revisions")
    elif revision_count <= 8:
        concern_points += 18
        reasons.append("a limited number of visible revisions")

    if window_minutes is not None and window_minutes < 15:
        concern_points += 35
        reasons.append("a very short visible drafting window")
    elif window_minutes is not None and window_minutes < 60:
        concern_points += 22
        reasons.append("a short visible drafting window")

    if unique_editor_count == 0:
        concern_points += 8
        reasons.append("no visible editor attribution")

    score = min(92, 20 + concern_points)

    if score >= 55:
        reason_text = _join_reasons(reasons)
        return (
            "needs_review",
            score,
            (
                f"'{document_title}' has {reason_text}. This does not prove AI use, "
                "but the visible process is thin enough to recommend teacher review."
            ),
            (
                "Use this as a conversation starter. Ask where the student drafted, "
                "whether text was pasted from another editor, and whether any tools "
                "were used during writing."
            ),
        )

    return (
        "low_concern",
        score,
        (
            f"'{document_title}' has a usable revision trail with enough visible "
            "drafting activity for a low-concern metadata review."
        ),
        (
            "No metadata-only warning stands out. This still does not verify authorship; "
            "it only means the visible revision trail looks reasonably complete."
        ),
    )


def _analysis_timeline(analysis: Dict, revisions: list, created_time: str) -> list:
    if not revisions:
        return _revision_timeline(revisions, created_time)

    timeline = [
        TimelineEvent(
            time=_short_time(analysis["first_revision"]),
            label="First visible revision",
            detail=f"Visible revision history begins at {analysis['first_revision']}.",
            severity="low",
        ),
        TimelineEvent(
            time=_short_time(analysis["last_revision"]),
            label="Last visible revision",
            detail=f"Visible revision history ends at {analysis['last_revision']}.",
            severity="low",
        ),
    ]

    if analysis["status"] == "needs_review":
        timeline.append(
            TimelineEvent(
                time="Review",
                label="Metadata review recommended",
                detail=analysis["summary"],
                severity="high",
            )
        )
    elif analysis["status"] == "insufficient_evidence":
        timeline.append(
            TimelineEvent(
                time="Review",
                label="Insufficient revision evidence",
                detail=analysis["summary"],
                severity="medium",
            )
        )

    return timeline + _revision_timeline(revisions, created_time)[-3:]


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
        return timestamp

    return timestamp.split("T", 1)[1][:5]


def _parse_google_time(timestamp: str) -> Optional[datetime]:
    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_between(start: Optional[datetime], end: Optional[datetime]) -> Optional[int]:
    if not start or not end:
        return None

    return max(0, int((end - start).total_seconds() // 60))


def _format_duration(minutes: Optional[int]) -> str:
    if minutes is None:
        return "Unknown"
    if minutes < 60:
        return f"{minutes} minutes"
    if minutes < 60 * 24:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m"

    days = minutes // (60 * 24)
    remaining_hours = (minutes % (60 * 24)) // 60
    return f"{days}d {remaining_hours}h"


def _format_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "Unknown"

    normalized = value.astimezone(timezone.utc)
    return normalized.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_revision_density(revision_count: int, window_minutes: Optional[int]) -> str:
    if window_minutes is None:
        return "Unknown"
    if window_minutes == 0:
        return f"{revision_count} revisions at one visible timestamp"

    revisions_per_hour = revision_count / max(window_minutes / 60, 1 / 60)
    return f"{revisions_per_hour:.1f} revisions/hour"


def _evidence_quality(revision_count: int, window_minutes: Optional[int]) -> str:
    if revision_count < 2:
        return "Insufficient"
    if revision_count >= 10 and window_minutes is not None and window_minutes >= 60:
        return "Strong"
    if revision_count >= 4:
        return "Moderate"
    return "Limited"


def _join_reasons(reasons: list) -> str:
    if not reasons:
        return "some metadata patterns worth checking"
    if len(reasons) == 1:
        return reasons[0]

    return f"{', '.join(reasons[:-1])}, and {reasons[-1]}"
