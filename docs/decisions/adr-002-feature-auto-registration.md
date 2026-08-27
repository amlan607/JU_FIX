# ADR-002: Features register themselves rather than editing a shared file

- **Status:** Accepted
- **Date:** Sprint 1

## Context

Six developers deliver six features in parallel on six branches during one
sprint. The obvious design has a shared registry that each feature edits:

- `app/models/__init__.py` importing every model
- `app/main.py` importing and mounting every router
- `src/App.jsx` importing and mounting every screen

Every branch touches all three files, so every pull request conflicts on all
three. Worse, the application fails to start whenever one feature is missing,
which means nobody can run `main` until all six have merged.

## Decision

Each layer discovers its own modules.

**Backend models** — `app/models/__init__.py` globs `*.py` in its own package
and imports each module, registering the tables on the metadata.

**Backend controllers** — `app/controllers/__init__.py` exposes
`collect_routers()`, which globs `*_controller.py`, reads the module level
`router` from each, and returns them. `app/main.py` mounts whatever it finds.

**Frontend routes** — `src/routes/registry.js` uses Vite's `import.meta.glob`
on `../features/*/routes.jsx`. Each feature folder exports a default array of
route objects:

```js
export default [
  { path: '/appointments', element: <MyAppointmentsPage />, roles: ['student', 'faculty'] },
  { path: '/verify-certificate', element: <VerifyCertificatePage />, layout: 'public' },
];
```

Adding a feature therefore means **adding files, never editing shared ones**.

## Consequences

**Positive**

- No merge conflicts on registry files. Pull requests touch only their own
  feature folder plus that feature's tests.
- The application starts and its tests pass with any subset of features merged,
  so `main` is never broken by a feature that has not landed yet.
- Each feature folder is genuinely self contained, which matches the Sprint 1
  requirement that each person own one complete feature.

**Negative**

- Registration is implicit. A reader cannot see the full route list in one file;
  they must look at the feature folders. This is mitigated by the naming
  convention (`*_controller.py`, `features/*/routes.jsx`) and by documenting it
  here and in the module docstrings.
- A module that fails to import is skipped rather than crashing loudly. The CI
  test suite catches this, because a missing router means the feature's API
  tests return 404.

## Alternatives considered

**Explicit registration with one added line per feature.** Readable, but produces
a conflict on every pull request and breaks `main` until all six features merge.
Rejected for the parallel sprint; it would be a reasonable choice for a team of
one or two.
