# Taxonomy v1.0 Repo-Ready Update

This bundle contains the updated documents for the frozen Canonical Topic Taxonomy v1.0 decision.

The SQL snapshot is unchanged because no Phase 2 migration has been applied yet.

Files that changed:

- CANONICAL_TOPIC_TAXONOMY.md (new)
- DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md
- MASTER_TECHNICAL_SPECIFICATION.md
- INTELLIGENCE_CALENDAR_TECHNICAL_SPECIFICATION.md
- DATABASE_SCHEMA.md
- SCHEMA_CHANGELOG.md
- README.md
- SPECIFICATION_INTEGRATION_CHANGE_REPORT.md

CURRENT_SCHEMA.sql is included only as the unchanged Phase 1 baseline reference.

Before committing in the local repo, run:

```bash
grep -RInE '(^|[^A-Za-z])(Culture|Disasters)([^A-Za-z]|$)' docs
```

Review matches contextually. Ordinary prose references to culture or disasters are valid; obsolete canonical root lists using `Culture` or `Disasters` alone should be updated.
