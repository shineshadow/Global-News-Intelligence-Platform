# Canonical Topic Taxonomy

**Project:** Global News Intelligence Platform  
**Document:** `CANONICAL_TOPIC_TAXONOMY.md`  
**Taxonomy version:** `1.0`  
**Status:** Authoritative / Root Layer Frozen  
**Effective date:** July 24, 2026  

---

## 1. Purpose

This document is the authoritative source for the Global News Intelligence Platform's canonical hierarchical **topic taxonomy**.

The root layer is frozen at taxonomy version `1.0`. All documents, Stories, observed Events, Intelligence Calendar Events, Monitors, Alerts, Search filters, analytics, and Publisher Workspace workflows must reuse this taxonomy rather than creating competing topic vocabularies.

Geography, entities, document type, source type, editorial orientation, and other classification dimensions are separate from the topic taxonomy.

---

## 2. Canonical Root Topics — Taxonomy v1.0

The following 23 roots are authoritative:

```text
Politics
Law & Judiciary
War & Security
Foreign Affairs
Economy
Business
Technology
Energy
Health
Science
Environment
Society
Crime
Immigration
Media
Education
Religion
Arts, Culture & Entertainment
Disasters & Emergencies
Labor & Employment
Sports
Weather
Lifestyle & Human Interest
```

No additional top-level topic may be created merely because a subject is operationally important. New subjects should normally be placed as child or descendant topics beneath the most appropriate root and may be multi-labeled across roots when the content genuinely spans multiple domains.

---

## 3. Canonical Root Slugs and Sort Order

| Sort | Slug | Canonical name |
|---:|---|---|
| 10 | `politics` | Politics |
| 20 | `law-judiciary` | Law & Judiciary |
| 30 | `war-security` | War & Security |
| 40 | `foreign-affairs` | Foreign Affairs |
| 50 | `economy` | Economy |
| 60 | `business` | Business |
| 70 | `technology` | Technology |
| 80 | `energy` | Energy |
| 90 | `health` | Health |
| 100 | `science` | Science |
| 110 | `environment` | Environment |
| 120 | `society` | Society |
| 130 | `crime` | Crime |
| 140 | `immigration` | Immigration |
| 150 | `media` | Media |
| 160 | `education` | Education |
| 170 | `religion` | Religion |
| 180 | `arts-culture-entertainment` | Arts, Culture & Entertainment |
| 190 | `disasters-emergencies` | Disasters & Emergencies |
| 200 | `labor-employment` | Labor & Employment |
| 210 | `sports` | Sports |
| 220 | `weather` | Weather |
| 230 | `lifestyle-human-interest` | Lifestyle & Human Interest |

Root slugs are stable machine identifiers. Display-name changes should not silently change slugs.

---

## 4. Root Definitions

### Politics

Political institutions, political power, elections, parties, governance, public policy, political movements, and political accountability.

### Law & Judiciary

Courts, legal systems, constitutional issues, legislation as lawmaking/legal text, litigation, prosecution, legal rights, and judicial institutions.

### War & Security

Armed conflict, military affairs, defense, intelligence, terrorism, national security, strategic security, and related operations.

### Foreign Affairs

Diplomacy, international relations, alliances, treaties, bilateral and multilateral relations, international organizations, and foreign policy.

### Economy

Macroeconomics, monetary and fiscal policy, trade, financial systems and markets, inflation, growth, economic indicators, and economic policy.

### Business

Companies, industries, corporate activity, management, earnings, investment, mergers, commercial operations, and sector-specific business developments.

### Technology

Computing, software, telecommunications, artificial intelligence, semiconductors, cybersecurity, digital infrastructure, and emerging technologies.

### Energy

Energy production, generation, markets, fuels, power infrastructure, energy security, utilities, and energy policy.

### Health

Medicine, healthcare systems, public health, disease, pharmaceuticals, medical research, health policy, and healthcare delivery.

### Science

Scientific research, discoveries, space science, physical and life sciences, research institutions, and scientific policy.

### Environment

Climate, ecosystems, conservation, pollution, environmental regulation, biodiversity, natural resources, and environmental change.

### Society

Demographics, social issues, communities, civil society, social movements, inequality, family and population trends, and broad societal change.

### Crime

Criminal incidents, organized crime, fraud, corruption as criminal conduct, policing, criminal investigations, and public-safety crime reporting.

### Immigration

Migration, immigration policy, borders, asylum, refugees, visas, citizenship, deportation, and population movement across jurisdictions.

### Media

Journalism, news organizations, broadcasting, publishing, social platforms as media systems, press freedom, media regulation, and information ecosystems.

### Education

Schools, universities, students, teachers, academic policy, education systems, curricula, research education, and educational institutions.

### Religion

Religious institutions, faith communities, religious practice, theology in public life, religious freedom, and religion-related events.

### Arts, Culture & Entertainment

Film, television, music, books, visual and performing arts, cultural heritage, museums, entertainment industries, and cultural events.

### Disasters & Emergencies

Natural disasters, major accidents, fires, explosions, infrastructure failures, humanitarian emergencies, emergency response, and disaster recovery.

### Labor & Employment

Employment, unemployment, labor markets, wages, unions, strikes, workplace relations, workforce policy, and occupational safety.

### Sports

Competitive sports, teams, athletes, leagues, tournaments, governing bodies, sports policy, and major sporting events.

### Weather

Weather conditions, forecasts, meteorological phenomena, warnings, seasonal patterns, temperature, precipitation, storms, and climate-adjacent weather events.

### Lifestyle & Human Interest

Food, travel, fashion, leisure, hobbies, family and relationships, consumer lifestyle, personal-interest features, and human-interest stories.

---

## 5. Multi-Label Rule

Topic assignment is not mutually exclusive. A document may legitimately belong to multiple roots and multiple descendants.

Example:

```text
Article: Government blocks exports of advanced AI chips to a military end user.

Technology
└── Semiconductors

Foreign Affairs
└── Export Controls

War & Security
└── Defense Technology
```

The taxonomy must not force a document into a single artificial bucket.

---

## 6. Root Freeze Policy

Taxonomy version `1.0` freezes the 23-root layer.

The following require an explicit **major taxonomy-version change**, migration plan, and reclassification impact review:

- adding a new root;
- removing a root;
- merging or splitting roots;
- changing a root's semantic meaning materially;
- moving an established root beneath another root.

Normal taxonomy growth should occur below the root layer.

---

## 7. Versioning Policy

The taxonomy uses semantic-style versioning for classification meaning:

```text
1.0  Initial frozen 23-root taxonomy
1.1  Additive child topics, aliases, definitions, or non-breaking refinements
1.x  Further backward-compatible taxonomy expansion
2.0  Root-layer or other materially breaking semantic change
```

The exact taxonomy version used during automated classification must be retained with classification provenance.

Historical data must remain reclassifiable under a later taxonomy version.

---

## 8. Child and Descendant Development Rules

Child topics may be added as the platform expands without changing the root layer.

Examples of high-priority descendants include:

```text
Politics
└── Elections
    ├── Election Administration
    ├── Election Integrity
    ├── Campaigns
    ├── Polling
    ├── Election Law
    └── Certification / Recounts

Technology
├── Artificial Intelligence
├── Semiconductors
└── Cybersecurity

War & Security
└── Military
    ├── Military Exercises
    ├── Procurement
    ├── Naval Activity
    ├── Air Operations
    ├── Missile Activity
    ├── Space
    └── Nuclear
```

These examples are not exhaustive and do not freeze the descendant hierarchy.

When adding descendants:

1. prefer stable concepts rather than transient headlines;
2. avoid duplicating geography as a topic;
3. avoid encoding named entities as topics;
4. avoid duplicating document types as topics;
5. permit multi-label classification rather than forcing false exclusivity;
6. define each topic before production use;
7. assign stable machine slugs;
8. retire obsolete topics instead of deleting historical meaning;
9. version material semantic changes;
10. benchmark classification quality after substantial taxonomy expansion.

---

## 9. Relationship to Other Canonical Dimensions

The platform classifies content independently across:

```text
Geographies
Hierarchical Topics
Entities
Document Type
```

Examples:

```text
South Korea         -> Geography, not Topic
Lee Jae-myung       -> Entity, not Topic
court_decision      -> Document Type, not Topic
Politics            -> Topic
Elections           -> Topic descendant
```

Source organizational type, endpoint acquisition type, and publisher editorial orientation also remain separate dimensions.

---

## 10. Implementation Contract

The Phase 2 `topics` table must support arbitrary hierarchy depth and retain at minimum:

```text
id
parent_id
slug
name
description
depth
sort_order
taxonomy_version
is_active
created_at
updated_at
```

The initial seed migration must seed exactly these 23 roots at taxonomy version `1.0`.

Root identity should be based on stable slug rather than generated database ID. Database IDs may differ between environments.

---

## 11. Governance

This document is the authoritative root-topic reference.

`MASTER_TECHNICAL_SPECIFICATION.md` defines platform-wide contracts.

`DOCUMENT_CLASSIFICATION_TECHNICAL_SPECIFICATION.md` defines classification architecture, confidence, provenance, relationship models, and classifier behavior.

This document defines the canonical topic vocabulary and taxonomy-version policy.

When duplicated topic lists elsewhere disagree with this document, **this document controls the canonical taxonomy vocabulary** unless a later explicitly approved taxonomy version supersedes it.
