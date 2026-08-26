# Testing

## Running the suites

```bash
cd backend  && python -m pytest                    # 234 tests
cd backend  && python -m pytest --cov=app          # with coverage
cd frontend && npm run test                        # 60 tests
cd frontend && npm run test:watch                  # watch mode
```

CI runs both on every push and pull request.

## How the backend tests are organised

Two markers separate the two kinds of test:

- `@pytest.mark.unit` — business rules called directly against a database
  session, with no HTTP layer.
- `@pytest.mark.api` — endpoints called through `TestClient`, confirming wiring,
  status codes and role enforcement.

Run one kind:

```bash
python -m pytest -m unit
python -m pytest -m api
```

Each feature has one file of each kind, for example
`test_appointment_service.py` and `test_appointment_api.py`.

## Isolation

`tests/conftest.py` gives every test a fresh **in-memory SQLite** database
through a `StaticPool`, created and dropped per test. No test can see another
test's data, and the order tests run in cannot change the result.

The `client` fixture overrides the `get_db` dependency so the endpoint under
test uses that same in-memory session.

Helpers keep the tests readable: `make_user()`, `make_doctor()` and
`auth_header()`, which logs in and returns the bearer header.

## What is worth testing

The suite concentrates on rules that could cause real harm if they broke:

- A cancelled slot becomes bookable again, but an active one does not (FR-C2).
- A doctor with no treatment relationship cannot open a record (FR-D4).
- An administrator cannot read clinical content at all.
- Editing a record preserves the previous version (FR-D5).
- A tampered certificate fails signature verification (FR-F4).
- Logout genuinely invalidates the token, rather than trusting the client.
- Five failed logins lock the account (FR-A6).

Each test name states the rule it protects, so a failure reads as a sentence
about what broke.

## Frontend tests

Vitest with React Testing Library. Components are queried the way a user finds
them — by label, by role, by visible text — rather than by CSS class, so a
styling change does not break a test.

`src/test/renderWithProviders.jsx` wraps a component in the router and the auth
provider. `fetch` is stubbed per test to return the standard envelope, which
keeps component tests independent of a running backend.
