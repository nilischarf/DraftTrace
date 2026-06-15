# DraftTrace

DraftTrace is a prototype for a writing-process review tool: students submit a Google Doc, and teachers receive an evidence-based authorship report.

This first version is intentionally small. It has:

- React frontend
- FastAPI backend
- Mock authorship report endpoint
- Clear next steps for Google OAuth and Drive/Docs API integration

## Project Structure

```text
.
├── backend
│   ├── app
│   │   ├── main.py
│   │   ├── models.py
│   │   └── report_service.py
│   └── requirements.txt
└── frontend
    ├── index.html
    ├── package.json
    ├── src
    │   ├── App.jsx
    │   ├── api.js
    │   ├── main.jsx
    │   └── styles.css
    └── vite.config.js
```

## Run Locally

Start the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open the frontend URL printed by Vite, usually `http://localhost:5173`.

## Google OAuth Setup

Create a Google Cloud project, then:

1. Enable the Google Drive API.
2. Enable the Google Docs API.
3. Create an OAuth Client ID for a web application.
4. Add this authorized redirect URI:

```text
http://localhost:8000/auth/google/callback
```

Then create `backend/.env` from the example:

```bash
cp backend/.env.example backend/.env
```

Fill in:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173
```

Restart the backend after editing `.env`.

## Product Direction

The product should avoid saying "AI detected." Instead, reports should show authorship evidence:

- document timeline
- revision count
- large paste-like insertions
- drafting duration
- missing or insufficient evidence
- teacher review recommendation

## Next Technical Milestones

1. Add Google OAuth.
2. Let a student pick a Google Doc.
3. Use Google Drive API to read revision metadata.
4. Use Google Docs API / export snapshots to compare text over time.
5. Replace mock report data with real revision-derived signals.
