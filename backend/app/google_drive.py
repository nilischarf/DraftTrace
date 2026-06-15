import re
from typing import Dict, List

from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.google_auth import get_credentials

DOC_ID_PATTERN = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def extract_google_doc_id(document_url: str) -> str:
    match = DOC_ID_PATTERN.search(document_url)

    if not match:
        raise HTTPException(status_code=400, detail="Enter a valid Google Docs URL.")

    return match.group(1)


def fetch_google_doc_metadata(document_url: str) -> Dict:
    doc_id = extract_google_doc_id(document_url)
    service = build("drive", "v3", credentials=get_credentials(), cache_discovery=False)

    try:
        file_metadata = (
            service.files()
            .get(
                fileId=doc_id,
                fields=(
                    "id,name,mimeType,createdTime,modifiedTime,webViewLink,"
                    "owners(displayName,emailAddress),"
                    "lastModifyingUser(displayName,emailAddress)"
                ),
            )
            .execute()
        )
        revisions = _fetch_revisions(service, doc_id)
    except HttpError as error:
        raise HTTPException(status_code=error.resp.status, detail=str(error)) from error

    return {
        "file": file_metadata,
        "revisions": revisions,
    }


def _fetch_revisions(service, doc_id: str) -> List[Dict]:
    revisions: List[Dict] = []
    page_token = None

    while True:
        response = (
            service.revisions()
            .list(
                fileId=doc_id,
                pageToken=page_token,
                pageSize=200,
                fields=(
                    "nextPageToken,"
                    "revisions(id,modifiedTime,keepForever,"
                    "lastModifyingUser(displayName,emailAddress))"
                ),
            )
            .execute()
        )
        revisions.extend(response.get("revisions", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            return revisions
