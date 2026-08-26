# Setup Guide

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- Git

## 1. Clone and enter the repository

```bash
git clone <your-repository-url>
cd JU_FIX
```

## 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set a real `JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create the schema and the demo dataset, then start the server:

```bash
python -m app.seed
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/api/docs`
- Health check: `http://127.0.0.1:8000/api/health`

## 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the backend,
so the browser sees one origin and no CORS handling is needed in the UI code.

## 4. Sign in

Every seeded account uses `JuFix@2026`.

| Role | University ID | What to try |
|---|---|---|
| Student | `STU-2021-370` | Book an appointment, view records and prescriptions |
| Doctor | `DOC-2001` | Confirm a booking, write a record, issue a prescription |
| Pharmacist | `PHR-3001` | Verify a prescription by reference and dispense it |
| Admin | `ADM-4001` | Approve registrations, view reports, export CSV |

## Resetting the database

The development database is a single file. Delete it and reseed:

```bash
cd backend
rm ju_fix.db
python -m app.seed
```

## Common problems

**`ModuleNotFoundError: No module named 'app'`** — run `uvicorn` and `pytest`
from inside the `backend` folder, not from the repository root.

**Frontend shows "Cannot reach the JU_FIX server"** — the backend is not
running, or it is not on port 8000. Check `vite.config.js`.

**`401` immediately after signing in** — the backend restarted and the in-memory
SQLite database was recreated, so the session token no longer exists. Sign in again.
