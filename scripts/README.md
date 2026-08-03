## System Dependencies

### Debian/Ubuntu run script:

```bash
bash scripts/install-sys-deps.sh
```
### Or in terminal:

```bash
sudo apt update

sudo apt install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    curl \
    git \
    build-essential \
    libpq-dev
```    

### Your dependency layers would then look like this

```text
OS / Debian/Ubuntu packages
    ↓
sudo apt install
    ↓
scripts/install-sys-deps.sh

Python packages
    ↓
pyproject.toml

JavaScript packages
    ↓
package.json
```

---

## Repository Test Procedure

Use the guarded test runner:

```bash
scripts/run-test-suite.sh
```

The runner deliberately executes:

```text
migration safety tests
        ↓
/var inode guard
        ↓
all non-migration regression tests
        ↓
/var inode guard
```

The test fixture cleans application tables only before each test and uses
`CONTINUE IDENTITY`. It does not repeat the cleanup after each test or reset
the 79 owned sequences. This bounds PostgreSQL relation-file churn while
still ensuring every test begins from empty application state.

The runner stops at 65% `/var` inode use by default. A non-migration
regression pass can consume roughly 20 percentage points of the current
inode pool, so this preserves headroom below filesystem exhaustion.
Override the threshold only for a deliberately provisioned test host:

```bash
GNI_TEST_INODE_LIMIT_PERCENT=75 scripts/run-test-suite.sh
```

Do not treat free bytes from `df -h` as sufficient. Check `df -i /var`;
PostgreSQL returns `No space left on device` when the filesystem exhausts
inodes even if gigabytes remain free.

## Artifact Signature Bootstrap

Import and activate the exact repository-pinned signature release with:

```bash
.venv/bin/python scripts/import_artifact_signatures.py
```

The importer verifies the separate manifest before opening its transaction,
then imports or returns the same active release idempotently. It fails closed
on changed bytes, unknown formats, ambiguous active evidence, or conflicting
stored release identity.

## Artifact Inspection Dependencies

Install the repository system dependencies before activating Artifact
acquisition:

```bash
bash scripts/install-sys-deps.sh
```

The inspection boundary requires Bubblewrap, libseccomp, ClamAV, and a
FreshClam-managed signature database under `/var/lib/clamav`. Scanner
readiness is checked inside the credential-free sandbox. Missing or stale
infrastructure has no fallback and prevents retrieval from beginning.

After installation or a signature update, run the real boundary smoke:

```bash
.venv/bin/python scripts/smoke_artifact_inspection.py
```

It verifies sandbox readiness, accepts a clean temporary payload, and rejects
the harmless industry-standard EICAR antivirus test payload. Temporary bytes
are removed when the smoke exits.

## Outbound Egress Smoke

Run the production DNS, TLS/SNI, IP-pinning, peer-verification, response-limit,
and loopback-refusal smoke with:

```bash
.venv/bin/python scripts/smoke_outbound_egress.py
```

The command makes one bounded request to `https://example.com/`, reports the
validated connected peer, and proves a direct loopback URL is refused before
connection.

## Phase 3 Feed Runtime Storage

Before any feed endpoint receives an active Phase 3 adapter configuration, set
both installation paths:

```bash
ARTIFACT_STAGING_ROOT=/var/lib/gni/artifacts/staging
ARTIFACT_CANONICAL_ROOT=/var/lib/gni/artifacts/canonical
PHASE3_FEED_CUTOVER_LIMIT=1
```

They must be distinct, non-nested directories on approved local storage. The
runtime has no fallback path. Missing configuration prevents the Phase 3
worker from starting, and a configured endpoint is never downgraded to the
legacy poller.

Keep the cohort limit at one for the first development canary. After the
signature, inspection, egress, migration, and repository gates pass, use the
Acquisition Health page to activate one eligible endpoint with an explicit
operator and reason. A successful activation is only `pending` until its first
Phase 3 run succeeds; review the run, Artifact, rejection, Document, and
schedule evidence before expanding the cohort.
