from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import AuthorshipReport, SubmissionRequest
from app.report_service import create_mock_report

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


@app.post("/reports", response_model=AuthorshipReport)
def create_report(submission: SubmissionRequest):
    return create_mock_report(submission)
