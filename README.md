# JU_FIX — Jahangirnagar University Medical Centre Automation System

A monolithic MVC web application that digitises the JU Medical Centre: account management, appointment booking, electronic health records, digital prescriptions, medical certificates and administrative reporting.

## Technology

| Layer          | Technology                                     |
| -------------- | ---------------------------------------------- |
| Backend        | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 |
| Database       | SQLite for development, PostgreSQL compatible  |
| Frontend       | React 18, Vite, React Router 6                 |
| Backend tests  | pytest                                         |
| Frontend tests | Vitest, React Testing Library                  |
| CI             | GitHub Actions                                 |
| Docs           | MkDocs Material                                |

> **Documentation note.** The UI design document names Node.js and Express for the backend, while `JU_FIX_complete_project_context.md` §10 and §14 specify Python/FastAPI with pytest. The project context is the source of truth, so the implementation is FastAPI. See `docs/decisions/adr-001-backend-stack.md`. The UI design document should be corrected to match.

## Running it locally

### Backend

```bash
cd backend

python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

# Create .env from the example and edit JWT_SECRET_KEY
cp .env.example .env

# Create the demo dataset
python -m app.seed

# Start the backend
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Interactive documentation is available at:

`http://127.0.0.1:8000/api/docs`

### Frontend

```bash
cd frontend

npm install

npm run dev
```

The application runs at `http://localhost:5173` and proxies `/api` to the backend.

## Demo accounts

Every seeded account uses the password `JuFix@2026`.

| Role       | University ID                                                                                  |
| ---------- | ---------------------------------------------------------------------------------------------- |
| Admin      | `ADM-4001`                                                                                     |
| Doctor     | `DOC-2001`, `DOC-2002`                                                                         |
| Pharmacist | `PHR-3001`                                                                                     |
| Faculty    | `FAC-1001`                                                                                     |
| Student    | `STU-2021-370`, `STU-2021-350`, `STU-2021-360`, `STU-2021-375`, `STU-2021-376`, `STU-2021-364` |

## Tests

```bash
cd backend
python -m pytest    # 234 tests

cd ../frontend
npm run test        # 60 tests
```

## Project structure

```text
JU_FIX/
├── backend/
│   └── app/
│       ├── core/           Config, database, security, dependencies, errors
│       ├── models/         SQLAlchemy models (the Model layer)
│       ├── schemas/        Pydantic request and response validation
│       ├── services/       Business rules (no web framework imports)
│       └── controllers/    FastAPI routers (the Controller layer)
├── frontend/
│   └── src/
│       ├── components/     Shared UI building blocks
│       ├── features/       One folder per feature, each with its own routes.jsx
│       ├── services/       API client
│       └── styles/         Design tokens and global stylesheet
└── docs/                   MkDocs source
```

## Feature ownership — Sprint 1

| Feature                            | Owner                              |
| ---------------------------------- | ---------------------------------- |
| Create Account and Login           | Oywon Islam (370)                  |
| Appointment Booking and Scheduling | Mir Mohaiminul Islam (350)         |
| Admin Dashboard and Reporting      | Amlan Dutta Rahul (360)            |
| Electronic Health Records          | Ziad Muhammad Tahzeeb Rahman (375) |
| Medical Certificate and Sick Leave | Shadman Rahman (376)               |
| Digital Prescription Management    | Md Sher Ali (364)                  |
