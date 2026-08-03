# 02 — Preference Resolution

**Status:** Draft

Effective preference order:

```text
1. system-enforced requirement
2. explicit session action or URL state
3. page-specific saved User preference
4. general saved User preference
5. application default
6. component fallback
```

System rules include security, authorization, data integrity, domain
constraints, validation, retention, and server limits. They are never
overridden by presentation preferences.

Temporary changes do not persist without an explicit Save or Remember action.
URL state controls the current visit but does not overwrite saved defaults.
Sensitive values never enter URLs. Invalid preferences fall back safely and
preference failure must not block workflow access.

Every persistent preference declares key, type, allowed values, default,
scope, storage, duration, cross-device behavior, migration, reset, owner, and
device applicability. General display preferences belong to User; relevance
and Attention weights belong to Attention Profile.

The UI-only American date/time preset approved by UXD-0003 remains mandatory
until another preset is approved through a UX Decision Record. User-specific
display timezone is a separate rendering preference and never rewrites stored
timestamps or changes canonical machine formats.
