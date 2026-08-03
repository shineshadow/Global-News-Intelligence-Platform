# 03 — Component Ownership

**Status:** Draft

Every reusable component has a permanent `CMP-####` identity, primary owner,
backup owner, documented contract, supported devices, states, dependencies,
preference behavior, lazy-loading behavior, consumers, limitations, and review
date.

The authoritative index is
[`component-registry/registry.yaml`](component-registry/registry.yaml). A
component is generally reusable only after its record is Approved. Explicitly
identified experimental work may consume Experimental components.

Changes are Patch, Compatible Feature, or Breaking. Breaking changes require
owner approval, affected-workflow review, migration instructions,
repository-wide usage search, release note, and a deprecation period where
practical.

A new component is not justified merely because an existing component is
inconvenient. Its proposal records evaluated components, why composition and
extension fail, its distinct contract, and ownership. Similar appearance never
permits merging distinct GNI domain semantics.
