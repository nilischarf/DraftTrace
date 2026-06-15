from datetime import datetime
from uuid import uuid4

from app.models import AuthorshipReport, SubmissionRequest, TimelineEvent


def create_mock_report(submission: SubmissionRequest) -> AuthorshipReport:
    """Return a realistic placeholder report until Google Docs data is connected."""
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
