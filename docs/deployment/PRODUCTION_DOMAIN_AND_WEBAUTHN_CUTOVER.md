# Production Domain and WebAuthn Cutover Guide

**Status:** Operational deployment guide  
**Applies to:** GNI production installation and first production Owner enrollment  
**Authority:** Deployment procedure only; it does not alter Owner authority or authentication policy

## Purpose

This guide defines the changes required when GNI moves from the development origin
`http://localhost:8000` to a production server with a valid HTTPS domain. It covers the WebAuthn
relying-party boundary, TLS and reverse-proxy requirements, service and infrastructure settings,
database cutover, Owner credential transition, production hardening, validation, and rollback.

The final production hostname must be chosen before production passkeys are enrolled. WebAuthn
credentials are cryptographically scoped to a relying-party ID (RP ID). A credential registered
for `localhost` cannot authenticate against a different production RP ID.

## 1. Final production identity

For an illustrative final hostname of `gni.example.com`, configure:

```env
APP_ENV=production

AUTH_RP_ID=gni.example.com
AUTH_RP_NAME=Global News Intelligence
AUTH_EXPECTED_ORIGIN=https://gni.example.com
AUTH_COOKIE_SECURE=true
```

`AUTH_RP_ID` contains only the hostname. It must not contain a scheme, port, path, query, or
fragment. `AUTH_EXPECTED_ORIGIN` is the exact externally visible origin and contains the HTTPS
scheme and hostname. Include a port only if production deliberately uses a non-default HTTPS port.

Use the exact application hostname as the RP ID unless the Owner explicitly approves broader
credential scope. Using a parent RP ID such as `example.com` permits its eligible subdomains to
share that relying-party scope and therefore broadens the security boundary.

Once production credentials exist, changing the RP ID is another credential migration. DNS,
branding, and reverse-proxy changes must not silently change it.

## 2. WebAuthn registration policy

Production retains the approved registration policy:

```text
attestation                       none
residentKey                       required
userVerification                  required
authenticatorAttachment           omitted
credentialProtectionPolicy        userVerificationRequired
enforceCredentialProtectionPolicy false
```

Omitting `authenticatorAttachment` keeps platform, hybrid-phone, and roaming hardware
authenticators eligible. GNI requests `credProtect` level 3 where supported without using the
optional extension as an eligibility gate. User verification itself remains mandatory and is
verified by the server during every registration and authentication ceremony.

## 3. DNS, TLS, and network boundary

Before enrollment:

1. Point the final production hostname to the production ingress address.
2. Install a publicly trusted TLS certificate for the exact hostname.
3. Redirect all plaintext HTTP requests to HTTPS.
4. Expose only required ingress ports, normally TCP 80 and 443.
5. Bind Uvicorn to loopback or a private application socket; do not expose it directly.
6. Keep PostgreSQL and Redis on loopback or an approved private network and deny public access.

The reverse proxy must preserve the external host and scheme. An Nginx deployment must include the
equivalent of:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Uvicorn must trust forwarded headers only from the known local reverse proxy. This is required for
correct secure-origin and CSRF evaluation; forwarded headers from arbitrary clients must not be
trusted.

## 4. Production environment and services

Create a production environment file readable only by the dedicated GNI service account. Replace
all development values, including:

- PostgreSQL URL, database, role, and strong credential;
- Redis and Celery broker/lock URLs;
- artifact staging and canonical storage paths;
- external provider and secret references;
- installation-owned acquisition-service identities;
- production session and operational settings approved for the installation.

The repository systemd units currently contain development-specific account and filesystem paths.
Production units must use:

- a dedicated, non-login GNI service account;
- the final application installation directory and virtual environment;
- `/etc/global-news-intelligence/gni.env` or another protected environment file;
- approved persistent data and log locations;
- the migration service as a successful prerequisite to application startup.

Run PostgreSQL migrations before starting the API and workers:

```bash
.venv/bin/python -m alembic upgrade head
```

Then start the target services and verify the API, database, Redis, workers, scheduled jobs, and
artifact storage.

## 5. Owner credential transition

### 5.1 Migrating the development database

The current Owner account and authentication evidence may be retained, but the existing
`localhost` passkey cannot authenticate at the production domain. The localhost browser session
also cannot transfer because cookies are host-bound and production uses secure `__Host-` cookies.

Use this controlled transition:

1. Confirm that the Owner has securely retained the unused recovery codes before migration.
2. Back up and restore the approved database into production.
3. Deploy GNI at the final HTTPS origin with the final RP ID.
4. Open `/auth/recover` at the production domain.
5. Consume one recovery code to obtain a registration-only enrollment grant.
6. Register a new passkey at the production domain.
7. Confirm logout and a fresh production-domain login.
8. Add at least one additional production authenticator.
9. Revoke the obsolete localhost credential from the Owner account.
10. Rotate the recovery-code set because one code was consumed during cutover.

A recovery code never creates a normal session. It permits only registration of a replacement
passkey; successful verified registration is the transition to an authenticated session.

### 5.2 Starting with an empty production database

If production intentionally begins with an empty database, run the first-Owner bootstrap only
after the final HTTPS origin and RP ID are active:

```bash
.venv/bin/python -m scripts.auth_admin bootstrap-owner \
  --username OWNER_USERNAME \
  --display-name "GNI Owner" \
  --reason "Initial production Owner bootstrap"
```

Open the emitted single-use enrollment URL only at the final production domain. Save the generated
recovery codes immediately and register at least one additional authenticator before declaring the
cutover complete.

### 5.3 Staging domains

Passkeys registered for a staging hostname are staging credentials. They do not become production
credentials merely because the same code or database is later deployed elsewhere. Test the flow
in staging, but enroll production credentials only at the final production RP ID and origin.

## 6. Credential inventory

The active-passkey ceiling counts registered credentials, not browsers, devices, or sessions.
A synchronized passkey may be usable on multiple compatible devices through its credential
provider. A hardware security key registered once may be used through multiple compatible devices
and browsers. Separate authenticators or credential providers may create separate GNI credentials.

The current ceiling remains six active passkeys per account and is enforced in both the service and
PostgreSQL. Raising it is a separate Owner decision and requires coordinated application, database
trigger, test, and documentation changes.

## 7. Production security gates

Complete and review these controls before public exposure:

- exact trusted-host enforcement for the approved hostname;
- explicit reverse-proxy and forwarded-header trust boundaries;
- rate limits for login, recovery, and enrollment endpoints;
- HTTP Strict Transport Security after HTTPS is proven stable;
- a reviewed Content Security Policy and browser security headers;
- firewall isolation for Uvicorn, PostgreSQL, Redis, and internal workers;
- protected secrets with least-privilege filesystem permissions;
- encrypted database and artifact backups with a tested restore procedure;
- authentication, authorization-denial, recovery-use, and service-health monitoring;
- a health endpoint exposure policy appropriate to the production network;
- at least two working Owner authenticators and securely stored recovery codes.

These gates preserve the rule that authentication and recovery information is internal and Owner
information. Operational tooling and future Admin UI work must not reduce Owner access to that
information.

## 8. Cutover verification

The production cutover is not complete until all applicable checks pass:

```text
DNS resolves to approved ingress                         pass
TLS chain and hostname validation                        pass
HTTP redirects to HTTPS                                  pass
untrusted Host values rejected                           pass
forwarded headers trusted only from approved proxy       pass
database migration at repository head                    pass
API, PostgreSQL, and Redis health                         pass
workers and schedulers active                            pass
production Owner passkey registration                    pass
fresh logout and passkey login                           pass
required UV verified                                     pass
second Owner authenticator registered                    pass
localhost credential revoked                             pass
recovery codes rotated and stored                        pass
backup and restore exercise                              pass
authentication and recovery audit evidence visible       pass
```

Record the final hostname, RP ID, expected origin, certificate ownership, deployment revision,
migration revision, service identities, verification results, operator, timestamp, and Owner
approval in the production change record. Never record raw enrollment links, session tokens,
private keys, or recovery codes.

## 9. Rollback

An application rollback must preserve the production hostname, RP ID, expected origin, database,
and authentication evidence. Do not revert production configuration to `localhost` after
production credentials have been issued. Do not downgrade the database unless a separately tested
and explicitly approved data migration requires it.

If the new release fails before production enrollment, keep ingress closed and restore the last
known-good application revision. If it fails after enrollment, preserve the database and credential
records, restore a compatible application revision, verify login, and retain immutable audit
evidence. Recovery codes remain emergency registration authority and must never be converted into
a password or direct-login bypass.

