from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from app.google_auth import create_authorization_url, exchange_code_for_token, frontend_url, google_status
from app.google_drive import fetch_google_doc_metadata, probe_revision_snapshots
from app.models import AuthorshipReport, SnapshotProbeRequest, SubmissionRequest
from app.report_service import create_mock_report

load_dotenv()

app = FastAPI(title="DraftTrace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/google/status")
def get_google_status():
    return google_status()


@app.get("/auth/google/start")
def start_google_auth():
    return {"authorization_url": create_authorization_url()}


@app.get("/auth/google/callback")
def google_auth_callback(code: str, state: str = ""):
    exchange_code_for_token(code=code, state=state)
    return RedirectResponse(f"{frontend_url()}/?google=connected")


@app.post("/reports", response_model=AuthorshipReport)
def create_report(submission: SubmissionRequest):
    google_document = fetch_google_doc_metadata(submission.document_url)
    return create_mock_report(submission, google_document=google_document)


@app.post("/debug/revision-snapshots")
def debug_revision_snapshots(request: SnapshotProbeRequest):
    return probe_revision_snapshots(
        document_url=request.document_url,
        max_revisions=request.max_revisions,
    )
