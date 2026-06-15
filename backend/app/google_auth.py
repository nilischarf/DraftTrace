import json
import os
from pathlib import Path
from typing import Dict, Optional

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

TOKEN_PATH = Path(".drafttrace_google_token.json")
STATE_PATH = Path(".drafttrace_oauth_state.json")


def google_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


def frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


def redirect_uri() -> str:
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


def get_client_config() -> Dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri()],
        }
    }


def create_flow() -> Flow:
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    flow = Flow.from_client_config(get_client_config(), scopes=SCOPES)
    flow.redirect_uri = redirect_uri()
    return flow


def create_authorization_url() -> str:
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    STATE_PATH.write_text(json.dumps({"state": state}), encoding="utf-8")
    return authorization_url


def exchange_code_for_token(code: str, state: Optional[str]) -> None:
    expected_state = _load_expected_state()

    if expected_state and state != expected_state:
        raise HTTPException(status_code=400, detail="OAuth state did not match.")

    flow = create_flow()
    flow.fetch_token(code=code)
    TOKEN_PATH.write_text(flow.credentials.to_json(), encoding="utf-8")


def get_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        raise HTTPException(status_code=401, detail="Google account is not connected.")

    credentials = Credentials.from_authorized_user_info(
        json.loads(TOKEN_PATH.read_text(encoding="utf-8")),
        scopes=SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

    if not credentials.valid:
        raise HTTPException(status_code=401, detail="Google credentials are invalid.")

    return credentials


def google_status() -> Dict:
    return {
        "configured": google_configured(),
        "connected": TOKEN_PATH.exists(),
        "scopes": SCOPES,
        "redirect_uri": redirect_uri(),
    }


def _load_expected_state() -> Optional[str]:
    if not STATE_PATH.exists():
        return None

    try:
        state_data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    return state_data.get("state")
