# Site-Wide Authentication and Authority Foundation Implementation

**Date:** 2026-08-25  
**Status:** OWNER-ACCEPTED IMPLEMENTATION

This change replaces the discarded password draft with a passwordless WebAuthn foundation. It
adds stable users and roles, up to six passkeys per account, short-lived single-use ceremonies,
opaque hashed sessions, hashed single-use recovery codes, registration-only enrollment grants,
append-only authentication evidence, centralized site/API authorization, CSRF enforcement, and
stable authenticated actor provenance.

The browser login and enrollment surfaces use native WebAuthn. Authentication requires UV.
Registration requires a discoverable credential, requires UV, omits `authenticatorAttachment`,
uses `attestation: none`, and requests `userVerificationRequired` credential protection where the
authenticator supports `credProtect`. The optional extension is not enforced as an eligibility
gate, so UV-capable platform, hybrid-phone, and roaming hardware authenticators remain available;
UV itself remains mandatory and is verified server-side.

Recovery deliberately cannot authenticate. It consumes one hashed recovery code and creates only
a short-lived replacement-passkey enrollment grant. Successful verified registration is the sole
transition back to a normal session.

The first Owner is created by `python -m scripts.auth_admin bootstrap-owner`; the command prints a
single-use enrollment URL once. It accepts no password. Existing site and API routes are protected,
while health, static assets, login, enrollment, and recovery entry points remain public as required.

The implementation preserves the governing `OWNER_*` precedence: Owner remains the highest role,
caller-submitted actor fields no longer govern protected mutations, and the existing Owner-policy
ledger remains the robots-override authority. Authenticated robots GUI work remains the next slice.

## Verification

```text
focused authentication, migration, and affected web UI suite   24 passed
fresh migration upgrade                                         passed
Alembic ORM/schema drift check                         no operations
changed authentication-slice Ruff checks                         passed
repository diff whitespace check                                passed
full repository attempt                                 497 passed
remaining full-run setups                         11 infrastructure errors
```

The full-run errors were not assertion failures. Repeated whole-schema PostgreSQL truncation in
the temporary review cluster created hundreds of thousands of relation files and the server
reported `No space left on device`. The temporary cluster was replaced, after which the fresh
migration, focused suite, and zero-drift check passed.
