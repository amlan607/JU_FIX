# Architecture

## Style: Monolithic MVC

JU_FIX is one deployable application backed by one relational database. A
monolith suits a six person team on a one semester project: one repository, one
deployment, one test command, and no distributed transactions to reason about.

```
Browser (React)
      │  HTTP + JSON, all responses shaped {success, data, error}
      ▼
Controller layer   app/controllers/*_controller.py
      │  Validates the request shape, delegates, wraps the result
      ▼
Service layer      app/services/*_service.py
      │  Business rules. No FastAPI imports anywhere in this layer.
      ▼
Model layer        app/models/*.py  (SQLAlchemy)
      ▼
Database (SQLite in development, PostgreSQL compatible)
```

### Why the service layer imports no web framework

Business rules are tested directly against a database session, with no HTTP
round trip. That is why the suite has roughly twice as many service tests as API
tests: the rules are cheap to test in isolation, and the API tests then only need
to confirm wiring, status codes and role enforcement.

## The response envelope

Every endpoint answers with the same shape:

```json
{ "success": true,  "data": { }, "error": null }
{ "success": false, "data": null, "error": { "code": "conflict", "message": "…", "details": null } }
```

`app/core/responses.py` builds it and `app/core/errors.py` guarantees that even
an unhandled exception is returned in the same shape, so the frontend never has
to special case a failure.

## Error handling

Services raise a domain exception; they never raise `HTTPException`.

| Exception | HTTP | Used when |
|---|---|---|
| `ValidationError` | 400 | A business rule rejects the input |
| `AuthenticationError` | 401 | Credentials missing, invalid, revoked or expired |
| `PermissionDeniedError` | 403 | Authenticated but not allowed |
| `NotFoundError` | 404 | The resource does not exist |
| `ConflictError` | 409 | Conflicts with existing state, e.g. a double booking |

## Security decisions

- Passwords are stored as **bcrypt hashes** only. Hashing is one way; the system
  cannot recover a password, which is why reset issues a new one (FR-A3).
- JWTs carry a `jti` claim and every issued token has a row in `session_tokens`.
  Logout sets `revoked_at`, so the token stops working immediately rather than
  relying on the browser discarding it (FR-A9).
- Authorisation is decided on the backend on every request. The frontend hides
  controls for convenience only; removing that in the browser grants nothing.
- Login returns one identical message for an unknown account and a wrong
  password, so the endpoint cannot be used to discover which IDs exist.
- Clinical access needs a **treatment relationship**, not merely a doctor
  account (FR-D4). See `docs/features/medical-records.md`.

## Audit trail

`app/core/audit.py` appends to `audit_logs` inside the same transaction as the
change it describes, so an action and its audit entry commit or roll back
together. Entries record who, what and when — never clinical content.
