# UXD-0001: Use “Lite” as the Product-Facing Name for Light Mode

## Status

Approved

## Decision Date

2026-08-03

## Owner

GNI owner

## Reviewers

- GNI owner
- UI foundation

## Context

Tabler, browsers, and implementation libraries conventionally call the bright
appearance mode `light`. GNI requires stable product terminology independent
of framework labels.

## Decision

`Lite` is the only product-facing name for the bright appearance mode. `Dark`
is the product-facing name for the dark mode. Technical code may retain
`light` when it is the framework value.

## Scope

All appearance selectors, settings, menus, help, user documentation, messages,
preferences, and UI components.

## Precedence

This decision controls over framework, component-library, browser, OS,
third-party theme, generated-label, and developer-shorthand terminology. A
higher system security or domain rule may control behavior but does not rename
the product mode.

## Reasons

One stable product term prevents internal framework language from leaking into
the operator experience and avoids inconsistent Light/Lite labels.

## Alternatives Considered

### Use “Light” Everywhere

Rejected because the owner selected `Lite` as GNI's product terminology.

### Display Framework Values Directly

Rejected because framework implementation terms do not govern GNI product
language.

## Consequences

- User-facing copy uses `Lite` and `Dark`.
- Preference values are `lite` and `dark`.
- An adapter maps `lite` to a framework value such as `light`.
- Tests reject product-facing `Light` labels.
- Technical documentation may say `light` only for the implementation value.

## Affected Components

- CMP-0001
- CMP-0002

## Affected Workflows

- All operator and administration workflows with appearance controls

## Related Records

- None

## Supersedes

None

## Superseded By

None

## Implementation Status

In Progress

## Notes

The current shell implements Dark only; Lite remains required UI work.
