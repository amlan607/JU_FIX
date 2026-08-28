# Accounts and Authentication

**Owner:** Oywon Islam (370) · **Requirements:** FR-A1 – FR-A9

## What it does

Creates accounts for the five roles, verifies the contact method, signs users in
with a JWT, routes them to the right dashboard, and lets them recover a
forgotten password or edit their own profile.

## Account lifecycle

```
register  →  pending_verification
                    │  verify the emailed token
                    ▼
      student / faculty  →  active
      doctor / pharmacist / admin  →  pending_approval  →  (admin decides)  →  active
```

A doctor, pharmacist or admin registration is never usable until an
administrator approves it (FR-J1). That approval is Amlan's feature; this
feature puts the account into the queue.

## Password policy — FR-A3

At least 8 characters with at least one uppercase letter, one lowercase letter,
one digit and one special character. Enforced in `app/schemas/auth.py` on the
backend and mirrored in `passwordPolicy.js` for live feedback while typing. The
backend is the authority; the frontend copy exists only so the user does not
need a round trip to learn the rule.

Passwords are stored as **bcrypt hashes**. Hashing is one way, so the system
cannot show a user their password — it can only issue a new one.

## Account lockout — FR-A6

Five consecutive failed logins start a 15 minute lock. A successful login resets
the counter. Both values come from configuration, not from literals in the code.

## Why login gives one error message

An unknown university ID and a wrong password produce the identical message.
If they differed, anyone could submit IDs and learn which ones exist.

## Logout actually invalidates the session — FR-A9

Every issued JWT carries a `jti` claim and has a row in `session_tokens`. Logout
sets `revoked_at`, and `get_current_user` rejects any token whose row is revoked.
A copied token therefore stops working the moment the user signs out, instead of
remaining valid until it expires. This implements Consistency Note 11.4.

Completing a password reset revokes **every** active session for that account,
because a password change should end sessions opened with the old one.

## Verification tokens in development

`ENVIRONMENT` is not `production`, so `/auth/register` and `/auth/forgot-password`
return the token in the response body. This lets the team complete the flow with
no mail server. In production those fields are `None` and the token is emailed.

## Files

| Layer | Path |
|---|---|
| Schemas | `backend/app/schemas/auth.py` |
| Service | `backend/app/services/auth_service.py` |
| Controller | `backend/app/controllers/auth_controller.py` |
| Tests | `backend/tests/test_auth_service.py`, `test_auth_api.py` |
| Screens | `frontend/src/features/auth/` |
