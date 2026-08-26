# Site-Wide Authentication and Authority Foundation

**Owner decision:** 2026-08-25  
**Status:** IMPLEMENTED CANDIDATE  
**Migration:** `b8d0f2a4c6e8`

## Governing authority

The authenticated Owner is GNI's highest application authority. Authentication proves which
human is acting; it does not create a policy tier above the Owner and does not narrow any
authority in `OWNER_*` documents. The Owner role alone carries `owner.policy`. Administrator
and User roles cannot silently inherit, replace, or veto Owner authority.

The database preserves the final active Owner assignment. This is an ordinary safety guard,
not a claim that the project Owner lacks installation, database, or code authority.

## Passwordless contract

GNI has no password credential or password-login path. Primary authentication uses discoverable
WebAuthn/FIDO2 passkeys through the pinned Python distribution `webauthn==3.0.0`.

Every registration and authentication ceremony requires user verification. The authenticator,
not GNI, performs the local PIN, biometric, or device-unlock check. Registration requests:

```text
residentKey                         required
userVerification                   required
credentialProtectionPolicy         userVerificationRequired
enforceCredentialProtectionPolicy  false
```

The last two values request `credProtect` level 3 where supported without rejecting an otherwise
valid UV-capable authenticator that does not implement `credProtect`. GNI records whether the
attestation extension output confirms that level; absence of an extension output remains
`unconfirmed`, never falsely reported as confirmed. `authenticatorAttachment` is omitted so
platform, hybrid-phone, and roaming hardware authenticators remain eligible. Authentication
verification also requires the UV flag.

RP ID and expected origin are installation-owned settings and must match the deployed HTTPS
origin. Development localhost is the only non-HTTPS exception permitted by WebAuthn clients.

## Credentials and sessions

An account may have at most six active passkeys. Both the service transaction and a PostgreSQL
trigger enforce the ceiling. Credential IDs, public keys, counters, device/back-up state,
transports, AAGUID, UV requirement, credProtect request/confirmation, and use/revocation times
are retained. Private keys, PINs, biometric data, and device-unlock secrets never enter GNI.

Challenges and browser-binding tokens are random, short-lived, single-use, database-backed,
and stored with binding tokens hashed. Successful assertions create opaque sessions whose
session and CSRF tokens are stored only as SHA-256 digests. Protected site and API routes derive
the stable actor as `user:<public UUID>`; caller-supplied actor names have no authority.

## Recovery is not login

Recovery codes are high-value emergency material. A generated set contains ten random,
single-use codes by default; only SHA-256 digests are stored, and replacement generation revokes
unused codes from the former set.

A correct recovery code is atomically consumed into a short-lived, registration-only enrollment
grant. It does **not** create a site session, grant temporary site access, change roles, or bypass
user verification. Normal access resumes only after a new passkey is registered and its ceremony
passes required UV. Bootstrap and Owner-issued invitations use the same constrained enrollment
boundary.

## Authority roles

```text
Owner  site.read, site.operate, site.admin, owner.policy
Admin  site.read, site.operate, site.admin
User   site.read
```

The User role remains read-only until resource-scoped user authority is deliberately specified.
All unsafe cookie-authenticated requests require CSRF validation. Authentication, recovery,
authority denial, session, credential, and role events are append-only evidence.

## Owner and Admin UI obligation

Passkey inventory, device/back-up state, credProtect confirmation, active sessions, recovery-code
state, role assignments, denials, and authentication events are internal **and Owner information**.
They must be exposed in the future authenticated Owner/Admin interface. Their current partial UI
does not reclassify them as internal-only and does not reduce operational Owner access.

The next authority UI must let an authenticated Owner invite identities, assign permitted roles,
inspect and revoke credentials/sessions, rotate recovery codes, and exercise the existing robots
override service. It must call the existing authority services rather than inventing a UI-owned
authority store.

## Acceptance requirements

```text
no password table, field, form, verifier, or fallback
registration and authentication both require UV
registration requests credProtect userVerificationRequired
no more than six active passkeys per account
raw session, enrollment, binding, and recovery secrets are not persisted
recovery consumes one code and creates no authenticated session
only verified replacement-passkey registration restores access
site/API access and unsafe-request CSRF enforcement are centralized
stable authenticated actor replaces caller-supplied actor authority
final active Owner assignment is database-protected
authentication events are append-only
```
