# ADR-001: Backend stack is Python and FastAPI

- **Status:** Accepted
- **Date:** Sprint 1

## Context

Two project documents disagreed about the backend technology.

- `ui-design-all-12-features.md` names **Node.js with Express**.
- `JU_FIX_complete_project_context.md` §10 (Project-Wide Technical Decisions)
  and §14 (Quick Reference) name **Python with FastAPI**, and **pytest** as the
  backend test framework.

The project context also defines the source of truth hierarchy, which places the
approved architecture decisions above later design artefacts, and requires that
a difference between documents be **identified rather than silently resolved**.

## Decision

The backend is implemented in **Python 3.12 with FastAPI**, SQLAlchemy 2 and
Pydantic 2, tested with **pytest**. The frontend remains React with Vite, tested
with Vitest, which both documents agree on.

## Consequences

**Positive**

- Matches the documented project-wide technical decision, so the SRS, the wiki
  and the code agree.
- Pydantic validates every inbound payload from a schema definition, which
  removes hand written validation from the controllers.
- FastAPI generates the OpenAPI documentation at `/api/docs` from the same type
  hints, so the API reference cannot drift from the implementation.

**Negative**

- The team runs two toolchains: `pip` and `pytest` for the backend, `npm` and
  `vitest` for the frontend. Two install steps, two test commands.
- Developers switch between Python and JavaScript conventions. The coding
  standards already cover this: `snake_case` in Python, `camelCase` in JavaScript.

**Required follow-up**

The UI design document must be corrected so it no longer names Node.js and
Express. Until it is, the wiki contradicts the implementation.

## Alternatives considered

**Node.js with Express, as the UI document says.** One language across the whole
stack and a single `npm test`. Rejected because §10 and §14 of the project
context are the approved architecture decision, and the SRS and wiki both follow
that document.
