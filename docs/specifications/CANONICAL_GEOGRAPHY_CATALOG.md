# GNI Canonical Geography Catalog

**Catalog version:** 1.0  
**Snapshot date:** 2026-07-25  
**Authority:** GNI platform policy  
**Status:** Authoritative foundation

## Authority

The GNI platform—not the United Nations, Communist China, ISO, or any other
external political body—controls:

- whether a geography exists in the catalog;
- its canonical display name;
- its geography type;
- its political-status metadata;
- its hierarchy;
- whether it can be monitored, searched, filtered, or alerted on.

No PRC source or PRC political naming is permitted in the canonical geography
catalog.

External code standards may be retained only as technical interoperability
identifiers. They cannot exclude a geography or dictate its display name or
political status.

## Taiwan

Taiwan is a first-class canonical country:

```text
slug:           taiwan
name:           Taiwan
geography_type: country
ISO alpha-2:    TW
ISO alpha-3:    TWN
```

Taiwan is never represented as a province or subdivision of Communist China.

Any PRC-subordination formulation for Taiwan is prohibited as a platform
display name or classification label.

Taiwan's parent is a geographic region only. Geographic parentage does not
assign sovereignty.

## Separately monitorable nations and geographies

The foundation includes separate entries for:

```text
Taiwan
Hong Kong
Macao
Tibet
East Turkistan
Southern Mongolia
Palestine
Western Sahara
Kosovo
Kurdistan
Somaliland
```

`nation_or_homeland` exists so nations cannot be erased merely because an
external institution withholds a country code or diplomatic recognition.

## Catalog scope

The foundation includes:

- World;
- common global regions and subregions;
- all standard coded countries, dependencies, and geopolitical areas;
- platform-recognized countries omitted by external political processes;
- platform-recognized nations and homelands;
- platform-defined operational regions such as Indo-Pacific.

Total foundation rows: **286**.

## Configuration versus existence

Catalog inclusion answers:

```text
What geographies are available?
```

Site configuration separately answers:

```text
Which geographies are currently enabled for collection,
monitoring, filtering, alerts, and UI display?
```

Disabling a geography never removes it from the canonical catalog.

## Governance

Stable slugs are canonical machine identifiers.

New politically oppressed nations, de facto states, territories, maritime
areas, and regional concepts may be added through versioned catalog updates
without changing the core table design.

Canonical rows should be retired rather than destructively deleted once
classification history references them.
