import re
from typing import Dict, List

from fastapi import HTTPException
from google.auth.transport.requests import AuthorizedSession
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
    credentials = get_credentials()
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)

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


def probe_revision_snapshots(document_url: str, max_revisions: int = 8) -> Dict:
    doc_id = extract_google_doc_id(document_url)
    credentials = get_credentials()
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    session = AuthorizedSession(credentials)

    try:
        file_metadata = (
            service.files()
            .get(fileId=doc_id, fields="id,name,mimeType,webViewLink")
            .execute()
        )
        revisions = _fetch_revisions(service, doc_id)
        sampled_revisions = _sample_revisions(revisions, max_revisions)
        snapshots = [
            _probe_single_revision(service, session, doc_id, revision)
            for revision in sampled_revisions
        ]
    except HttpError as error:
        raise HTTPException(status_code=error.resp.status, detail=str(error)) from error

    successful_snapshots = [snapshot for snapshot in snapshots if snapshot["available"]]
    word_counts = [
        snapshot["word_count"]
        for snapshot in successful_snapshots
        if isinstance(snapshot.get("word_count"), int)
    ]

    return {
        "document": file_metadata,
        "revision_count": len(revisions),
        "sampled_revision_count": len(sampled_revisions),
        "snapshot_available": bool(successful_snapshots),
        "successful_snapshot_count": len(successful_snapshots),
        "largest_word_count_delta": _largest_delta(word_counts),
        "snapshots": snapshots,
        "note": _snapshot_probe_note(successful_snapshots),
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
                    "exportLinks,lastModifyingUser(displayName,emailAddress))"
                ),
            )
            .execute()
        )
        revisions.extend(response.get("revisions", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            return revisions


def _sample_revisions(revisions: List[Dict], max_revisions: int) -> List[Dict]:
    if len(revisions) <= max_revisions:
        return revisions

    last_index = len(revisions) - 1
    sampled_indexes = {
        round(index * last_index / (max_revisions - 1))
        for index in range(max_revisions)
    }
    return [revisions[index] for index in sorted(sampled_indexes)]


def _probe_single_revision(service, session: AuthorizedSession, doc_id: str, revision: Dict) -> Dict:
    revision_id = revision.get("id")
    base_result = {
        "revision_id": revision_id,
        "modified_time": revision.get("modifiedTime"),
        "last_modifier": _person_name(revision.get("lastModifyingUser", {})),
        "available": False,
        "word_count": None,
        "character_count": None,
        "reason": "",
    }

    try:
        revision_detail = (
            service.revisions()
            .get(
                fileId=doc_id,
                revisionId=revision_id,
                fields="id,modifiedTime,exportLinks,lastModifyingUser(displayName,emailAddress)",
            )
            .execute()
        )
    except HttpError as error:
        return {**base_result, "reason": f"Could not read revision detail: {error.resp.status}"}

    export_links = revision_detail.get("exportLinks", {})
    export_url = export_links.get("text/plain")

    if not export_url:
        return {
            **base_result,
            "reason": "No text/plain export link was available for this revision.",
        }

    response = session.get(export_url, timeout=20)

    if not response.ok:
        return {
            **base_result,
            "reason": f"Revision export request failed with HTTP {response.status_code}.",
        }

    text = response.text
    return {
        **base_result,
        "available": True,
        "word_count": _count_words(text),
        "character_count": len(text),
        "reason": "Snapshot exported as text/plain.",
    }


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _largest_delta(word_counts: List[int]) -> int:
    if len(word_counts) < 2:
        return 0

    return max(
        abs(current_count - previous_count)
        for previous_count, current_count in zip(word_counts, word_counts[1:])
    )


def _snapshot_probe_note(successful_snapshots: List[Dict]) -> str:
    if successful_snapshots:
        return (
            "At least one historical revision snapshot was exportable. Next step: "
            "turn this into a word-count timeline and large-insertion detector."
        )

    return (
        "No sampled historical revisions exposed text/plain snapshots. If this "
        "holds across real docs, DraftTrace should rely on metadata analysis or "
        "a capture workflow instead of historical text export."
    )


def _person_name(person: Dict) -> str:
    return person.get("displayName") or person.get("emailAddress") or "Unknown"
