# GFA-C — Canonical Entity-Type Taxonomy

## 1. Purpose and Scope

GFA-C establishes the canonical semantic foundation used by the Global News Intelligence Platform to identify, classify, relate, and externally map real-world entities and adjacent concept types encountered in global news.

The purpose of GFA-C is not to invent a proprietary ontology where established standards already exist. GNI instead adopts authoritative external standards for fundamental semantic meaning and maps those standards into normalized internal structures appropriate for a relational news-intelligence platform.

GFA-C defines:

* the authority hierarchy governing canonical entity classification;
* the boundary between entities, geography, events, points of interest, and abstract concepts;
* canonical entity-type identifiers and hierarchy;
* mappings between GNI types and external vocabularies;
* semantic mapping relationships between external and GNI concepts;
* entity-to-geography relationships;
* the event foundation required by the entity/concept boundary;
* the point-of-interest foundation required by the entity/concept boundary;
* standards-derived seed data;
* migration, integrity, and verification requirements.

GFA-C does not replace the existing canonical geography or topic systems.

GFA-C also does not require GNI's physical relational schema to reproduce the physical structure of any external ontology. External standards determine semantic meaning. GNI determines the internal normalized architecture used to preserve that meaning.

---

## 2. Authority and Standards

GFA-C uses an explicit authority hierarchy.

```text
IPTC Concept Nature
    ↓
Primary authority for fundamental
news-domain concept nature

Schema.org
    ↓
Preferred authority for standardized
practical subtype mappings

Wikidata
    ↓
Deep ontology mappings,
specialized classes, and
entity-resolution interoperability

W3C SKOS
    ↓
Semantic relationship vocabulary
for mappings between concept schemes
```

### 2.1 IPTC

The International Press Telecommunications Council is the primary authority for fundamental concept nature within GFA-C because GNI is specifically a news-intelligence platform.

IPTC NewsML-G2 provides a standardized news-industry mechanism for expressing concepts referenced by news content and distinguishes real-world concepts from abstract concepts. Its Concept Nature vocabulary defines the following fundamental concept natures: `person`, `organisation`, `animal`, `geoArea`, `poi`, `object`, `event`, and `abstract`.

| IPTC Concept Nature | Meaning                                             |
| ------------------- | --------------------------------------------------- |
| `person`            | Person                                              |
| `organisation`      | Organization                                        |
| `animal`            | Animal                                              |
| `geoArea`           | Geopolitical/geographic area                        |
| `poi`               | Point of interest                                   |
| `object`            | Real-world object                                   |
| `event`             | Event                                               |
| `abstract`          | Concept that does not represent a real-world entity |

IPTC Concept Nature establishes the primary high-level semantic boundary for GNI.

It does not dictate that all IPTC concept natures must be stored in the same GNI table or subsystem.

```text
PRIMARY AUTHORITY

IPTC News Architecture
IPTC NewsML-G2
IPTC Concept Nature NewsCodes
             │
             ▼
GNI Canonical Concept Foundation
```

### 2.2 Schema.org

Schema.org is the preferred secondary authority for standardized practical subtypes where a suitable Schema.org type exists.

Schema.org defines a large hierarchical vocabulary of types. Types inherit from parent types and may have more than one supertype. The current hierarchy includes broad classes such as `Person`, `Organization`, `Place`, `Event`, `Product`, `CreativeWork`, and `MedicalEntity`, together with more specialized types.

For example, Schema.org's `Organization` hierarchy includes standardized subtypes such as:

```text
Organization
├── Corporation
├── EducationalOrganization
├── GovernmentOrganization
├── MedicalOrganization
├── NGO
├── NewsMediaOrganization
├── PoliticalParty
├── ResearchOrganization
├── SportsOrganization
└── WorkersUnion
```

Schema.org explicitly defines `GovernmentOrganization` as a governmental organization or agency.

Schema.org identifiers retain their official native spelling and case in external mappings.

Schema.org uses TitleCase for type names and lowerCamelCase for property names.

GNI does not adopt Schema.org casing for internal canonical identifiers.

Example:

```text
Schema.org identifier:
GovernmentOrganization

GNI canonical slug:
government_organization
```

The mapping between the two is explicit and must never be reconstructed algorithmically from capitalization or spelling.

### 2.3 Wikidata

Wikidata provides the preferred deep ontology and entity-resolution interoperability layer.

Wikidata distinguishes individual instances from classes primarily through:

```text
P31  instance of
P279 subclass of
```

An instance represents an individual or specific thing. A class represents a collection of instances. `P279` links more specific classes to broader classes and forms a hierarchy of classes.

For example:

```text
specific person
    instance of → human

specific election
    instance of → public election

specialized class
    subclass of → broader class
```

Wikidata permits an item to participate in multiple classes and does not impose simple object-oriented inheritance semantics. GNI must therefore preserve Wikidata mappings explicitly rather than assuming that Wikidata's class graph can be copied directly into the GNI taxonomy.

Wikidata is particularly valuable for specialized classes and identity resolution involving concepts such as:

```text
election commissions
intelligence agencies
central banks
military units
armed groups
courts
legislatures
international organizations
missiles
fighter aircraft
warships
diseases
pathogens
treaties
elections
```

Wikidata QIDs and other native identifiers are preserved unchanged in the external mapping layer.

### 2.4 W3C SKOS Mapping Semantics

GNI must not assume that an external ontology concept and a GNI concept are always exactly equivalent.

W3C SKOS provides standardized mapping relationships for connecting concepts belonging to different concept schemes:

```text
exactMatch
closeMatch
broadMatch
narrowMatch
relatedMatch
```

`exactMatch` represents a high degree of confidence that concepts can be used interchangeably across a broad range of information-retrieval applications.

`closeMatch` represents concepts sufficiently similar for some interoperability purposes without asserting full equivalence.

`broadMatch` and `narrowMatch` represent hierarchical mappings.

`relatedMatch` represents an associative mapping.

GNI therefore freezes the following rule:

> External ontology mappings must record their semantic relationship explicitly. GNI must not assume every external mapping represents exact equivalence. SKOS mapping semantics are preferred where applicable.

### 2.5 External Identifier Preservation

External ontology identifiers retain their native syntax and case.

GNI canonical identifiers use lowercase `snake_case`.

Mapping between them is explicit and never inferred.

Examples:

```text
IPTC
organisation

Schema.org
GovernmentOrganization

Wikidata
Qxxxxxx

GNI
government_organization
```

The original IPTC identifier, Schema.org identifier, Wikidata QID, URI, QCode, or other authoritative external identifier must remain available without destructive normalization.

This rule is frozen for GFA-C.

---

## 3. GFA-C.1 — Existing Entity Inventory

**Status: COMPLETE**

A read-only database and repository preflight was performed before defining the canonical entity taxonomy.

### 3.1 Persisted Entity Inventory

The production database contained no persisted entity records:

```text
total_entities:          0
distinct_entity_types:   0
null_entity_types:       0
blank_entity_types:      0
```

The `entities.entity_type` column therefore contained no legacy production values requiring normalization.

### 3.2 Persisted Entity Alias Inventory

The production database contained no persisted entity aliases:

```text
entity_aliases: 0
alias_types:    0
```

No production alias taxonomy requires migration.

### 3.3 Existing Entity-Type Schema

Before GFA-C, entity type is represented as:

```text
entities.entity_type
    varchar(50)
    NOT NULL
```

The field is indexed but is not protected by a foreign key to a canonical entity-type reference table.

Entity type is therefore currently an unconstrained string dimension.

GFA-C must replace that semantic weakness with a canonical reference-backed entity-type foundation.

### 3.4 Existing Alias-Type Schema

`entity_aliases.alias_type` is a separate free-form string dimension.

Entity type and alias type represent different semantics:

```text
entity_type
    = what the entity is

alias_type
    = what kind of name or alias is being used
```

GFA-C must not collapse alias semantics into the entity-type taxonomy.

Normalization of alias types may be addressed independently when required.

### 3.5 Existing Repository Usage

Repository inspection found only one concrete hard-coded `entity_type` value outside the original migration:

```python
entity_type="agency"
```

This occurs in an entity-alias classification test involving the National Election Commission of South Korea.

Because no corresponding production entity data exists, `"agency"` is treated as a test fixture rather than an established canonical taxonomy decision.

The fixture may be changed when the standards-derived GNI entity vocabulary is established.

### 3.6 Migration Risk

Because both canonical entity tables are currently empty:

```text
legacy production entity rows:       0
legacy production alias rows:        0
legacy entity types to normalize:    0
legacy alias types to normalize:     0
```

GFA-C can establish the canonical entity foundation without preserving accidental production taxonomy values.

This allows the initial taxonomy to be standards-derived rather than backward-compatible with arbitrary legacy classifications.

---

## 4. GFA-C.2 — External Ontology / Standards Audit

**Status: COMPLETE / FROZEN**

### 4.1 Authority Hierarchy

GFA-C freezes the following authority hierarchy:

```text
LEVEL 1 — NEWS-DOMAIN SEMANTIC AUTHORITY

IPTC Concept Nature
    ↓
Defines fundamental news-domain concept nature


LEVEL 2 — STANDARDIZED PRACTICAL SUBTYPES

Schema.org
    ↓
Provides standardized subtype mappings
where appropriate


LEVEL 3 — DEEP ONTOLOGY AND IDENTITY

Wikidata
    ↓
Provides specialized class mappings
and external entity identity


MAPPING RELATIONSHIPS

W3C SKOS
    ↓
Defines semantic strength of mappings
between concept schemes
```

### 4.2 Fundamental-Class Rule

GNI does not invent fundamental entity classes when an appropriate external standard exists.

IPTC Concept Nature is the primary authority for fundamental news-domain concept nature.

Schema.org is the preferred authority for standardized subtype mappings.

Wikidata provides external ontology mappings for specialized classes and entity resolution.

### 4.3 Internal Identifier Rule

GNI canonical identifiers use:

```text
lowercase
ASCII where practical
snake_case
stable semantic meaning
```

External identifiers retain their authoritative native representation.

Example:

```text
Schema.org:
NewsMediaOrganization

GNI:
news_media_organization
```

The relationship must be stored explicitly.

### 4.4 Mapping Rule

External ontology mappings are first-class data.

GNI must preserve at minimum:

```text
external vocabulary
external identifier
external URI where applicable
GNI canonical concept
mapping relationship
```

Mapping equivalence must never be assumed solely because two labels appear similar.

SKOS mapping semantics are preferred where applicable.

### 4.5 Geography Separation

IPTC recognizes `geoArea` as a Concept Nature because NewsML-G2 needs a general mechanism for identifying concepts referenced by news content.

GNI does not interpret that external conceptual grouping as a requirement to store geography in the entity subsystem.

The following rule is frozen:

> Geography remains a distinct first-class GNI dimension and is never duplicated merely because an external ontology classifies geographic areas as named entities.

Therefore:

```text
IPTC geoArea
    → GNI geographies
```

The IPTC identifier remains preserved in the external standards mapping layer.

### 4.6 Abstract Concepts

IPTC defines `abstract` as a concept that does not represent a real-world entity. IPTC itself uses abstract subjects with controlled news vocabularies such as Media Topics.

The following rule is frozen:

> IPTC `abstract` concepts are routed to the appropriate GNI controlled-concept subsystem, generally topics, and are not automatically persisted as entities.

### 4.7 Person, Organisation, and Object

The following fundamental mappings are frozen:

```text
IPTC person
    → GNI entities

IPTC organisation
    → GNI entities

IPTC object
    → GNI entities
```

More specific canonical GNI entity types are determined through standards-derived subtype mappings established later in GFA-C.

### 4.8 Event and POI Boundary

GFA-C.2 establishes that IPTC `event` and `poi` require their own GNI semantic treatment rather than being blindly inserted into `entities`.

Their final GNI boundary rules are defined and frozen in GFA-C.3.

### 4.9 GFA-C.2 Frozen Invariants

The following are frozen:

```text
✓ IPTC is the primary authority for fundamental
  news-domain concept nature.

✓ Schema.org is the preferred authority for
  standardized subtype mappings.

✓ Wikidata provides deep ontology and
  entity-resolution mappings.

✓ SKOS provides preferred mapping semantics.

✓ GNI does not invent fundamental entity classes
  when an appropriate external standard exists.

✓ External identifiers retain their native syntax
  and case.

✓ GNI canonical identifiers use lowercase
  snake_case.

✓ External mappings are explicit and never
  reconstructed from spelling or capitalization.

✓ External mapping equivalence is never assumed.

✓ Geography remains a separate canonical GNI
  dimension.

✓ IPTC geoArea maps to GNI geographies.

✓ IPTC abstract concepts are generally routed
  to controlled-concept systems rather than entities.

✓ IPTC person, organisation, and object map
  into the GNI entity subsystem.

✓ Event and POI semantics are resolved through
  GFA-C.3 rather than forced into the entity table.
```

GFA-C.2 is complete.


## 5. GFA-C.3 — GNI Entity / Concept Boundary Mapping
    COMPLETE / FROZEN

### Canonical Boundary Rules

GNI maps external concept systems into distinct canonical subsystems according to semantic role. External ontology structure does not dictate physical GNI table organization.

```text
IPTC Concept Nature      GNI Canonical Subsystem

person               →   entities
organisation         →   entities
animal               →   entities
object               →   entities
poi                  →   points_of_interest
event                →   events
geoArea              →   geographies
abstract             →   appropriate controlled-concept subsystem,
                          generally topics
```

### Geography

Geography remains a distinct first-class GNI dimension and is never duplicated merely because an external ontology classifies geographic areas as named entities.

```text
IPTC geoArea
    → GNI geographies
```

Entities and events reference canonical GNI geography records through explicit relationships. Those relationships do not redefine or duplicate geography records.

```text
ENTITY ↔ GEOGRAPHY
EVENT  ↔ GEOGRAPHY
```

The existing free-text `entities.country_or_jurisdiction` field is not the long-term canonical entity-geography model and must be normalized during subsequent schema work.

### Events

IPTC `event` maps to the dedicated GNI events subsystem.

The planned GNI event foundation consists conceptually of:

```text
events
event_aliases
event_geographies
event_participants
```

Persistent and transient events are not separate fundamental event types. Persistence describes event identity/lifecycle behavior.

Events reference canonical GNI geographies and canonical GNI entities. Event relationships never create duplicate geography or entity records.

```text
EVENT ↔ GEOGRAPHY
EVENT ↔ ENTITY
```

### Points of Interest

IPTC `poi` maps to a dedicated GNI POI construct used as an event/entity decorator.

POI is not a canonical GNI entity type.

POI does not replace geography.

POI does not compensate for insufficient entity granularity.

Entity identity and POI characteristics are orthogonal. A highly granular real-world thing may be maintained as a canonical entity while simultaneously having POI information associated with it.

```text
ENTITY
    = identity of a real-world thing

POI
    = spatial, operational, descriptive, or situational
      information associated with an entity or event
```

GNI is intentionally designed for AI-assisted extraction and enrichment. The practical difficulty of manually cataloging highly granular entities is therefore not a valid reason to collapse useful entity distinctions.

A gate, entrance, room, checkpoint, facility component, or similarly fine-grained object may become a canonical entity when it has independently useful identity.

A POI may decorate that entity with additional information.

### POI Foundation

The logical POI architecture is:

```text
points_of_interest
        │
        ▼
point_of_interest_bindings
        │
        ├── entity
        └── event
```

A POI may be associated with both an entity and an event without being copied.

The same POI record may therefore provide reusable contextual information across multiple relationships.

POI information may include:

```text
address
coordinates
opening_hours
capacity
contact_information
access_information
details
valid_from
valid_to
metadata
provenance
external mappings
```

`details` is intentionally broad. It provides a controlled location for useful operational, descriptive, situational, or otherwise fine-grained information that does not justify creation of another first-class schema dimension.

`provenance` means POI information must support traceability to its source.

`external mappings` means POIs may participate in the same explicit ontology-mapping architecture used elsewhere in GNI. External mappings are not assumed to be literal columns on the POI table.

The exact relational representation of provenance, external mappings, bindings, keys, and constraints is deferred to GFA-C.4.

### POI Reuse Rule

A POI must not be copied merely because it is relevant to more than one object.

For example:

```text
POI X
    ├── decorates Entity A
    └── decorates Event B
```

rather than:

```text
Entity A → duplicate POI X1
Event B  → duplicate POI X2
```

### External Ontology Authority

GNI does not invent fundamental entity classes when an appropriate external standard exists.

The authority hierarchy is:

```text
IPTC Concept Nature
    → primary authority for fundamental news-domain concept nature

Schema.org
    → preferred authority for standardized subtype mappings

Wikidata
    → deep ontology mappings and entity-resolution interoperability
```

External ontology identifiers retain their native syntax and case.

GNI canonical identifiers use lowercase `snake_case`.

Mapping between external identifiers and GNI identifiers is explicit and never inferred from spelling or capitalization.

Original IPTC identifiers, Schema.org identifiers, Wikidata QIDs, URIs, QCodes, and other external identifiers must be preserved without destructive normalization.

External ontology mappings must record their semantic relationship explicitly. GNI must not assume every external mapping represents exact equivalence.

SKOS mapping semantics are preferred where applicable, including concepts such as:

```text
exactMatch
closeMatch
broadMatch
narrowMatch
relatedMatch
```

### Abstract Concepts

IPTC `abstract` concepts are routed to the appropriate GNI controlled-concept subsystem, generally topics, and are not automatically persisted as entities.

### Frozen GFA-C.3 Principle

GNI separates identity, geography, events, abstract concepts, and POI context rather than forcing all externally defined concepts into a single universal entity table.

External standards determine semantic meaning.

GNI determines the normalized internal architecture needed to preserve that meaning efficiently, explicitly, and without duplication.


## 6. GFA-C.4.1 — Canonical Entity-Type Schema

**Status: FREEZE CANDIDATE**

GFA-C.4.1 replaces the legacy single-valued free-text
`entities.entity_type` column with a normalized, reference-backed,
multi-valued entity-type assertion model.

The logical foundation is:

```text
entity_types
    │
    ├── entity_type_hierarchy_edges
    │
    └── entity_type_assignments
            │
            ├── entities
            └── semantic_assignment_methods
```

### 6.1 Canonical Entity Types

```text
entity_types

id
slug
name
description
is_active
metadata
created_at
updated_at
```

Rules:

```text
id
    bigint surrogate primary key

slug
    varchar(255)
    unique
    not null
    lowercase snake_case
    stable canonical identifier

name
    varchar(255)
    not null

description
    text
    null allowed

is_active
    boolean
    not null
    default true

metadata
    jsonb
    not null
    default {}
```

Generated database IDs are not canonical identifiers. Stable slugs are
used in APIs, configuration, seed data, and external references.

### 6.2 Entity-Type Hierarchy

Canonical entity types form a GNI-controlled directed acyclic graph
rather than a single-parent tree.

```text
entity_type_hierarchy_edges

id
parent_entity_type_id
child_entity_type_id
created_at
```

Relationships:

```text
parent_entity_type_id
    FK → entity_types.id
    ON DELETE RESTRICT

child_entity_type_id
    FK → entity_types.id
    ON DELETE RESTRICT
```

Required constraints:

```text
UNIQUE (
    parent_entity_type_id,
    child_entity_type_id
)

CHECK (
    parent_entity_type_id <> child_entity_type_id
)
```

The database must reject any insert or update that would introduce a
cycle. The implementation uses a deferred PostgreSQL constraint trigger
with a recursive traversal so that the DAG invariant does not depend
solely on application behavior.

### 6.3 Entity-Type Assignments

```text
entity_type_assignments

id
entity_id
entity_type_id
assignment_method
is_primary
confidence
evidence
provenance
valid_from
valid_to
is_active
superseded_at
created_at
updated_at
```

Relationships:

```text
entity_id
    FK → entities.id
    ON DELETE RESTRICT

entity_type_id
    FK → entity_types.id
    ON DELETE RESTRICT

assignment_method
    FK → semantic_assignment_methods.slug
    ON DELETE RESTRICT
```

An entity may have multiple active canonical type assignments, but only
one active assignment may be primary.

Required partial uniqueness:

```text
UNIQUE ACTIVE (
    entity_id,
    entity_type_id
)

UNIQUE ACTIVE PRIMARY (
    entity_id
)
```

Required checks:

```text
confidence IS NULL
    OR 0 <= confidence <= 1

valid_to IS NULL
    OR valid_from IS NULL
    OR valid_to >= valid_from
```

`is_active` expresses assertion lifecycle: an active row has not been
retired or superseded. `valid_from` and `valid_to` express real-world
temporal applicability. Consumers must not treat those concepts as
interchangeable.

Historical assignments are retained rather than destructively
overwritten. A changed primary type supersedes the prior primary
assignment and creates a new assertion.

### 6.4 Removal of `entities.entity_type`

The normalized canonical model does not retain
`entities.entity_type`.

During the additive implementation window the legacy column may remain
temporarily so old application code and new schema can be deployed
safely. GFA-C.6 removes it after repository consumers and fixtures have
migrated. It must not become a second canonical source of type truth.

### 6.5 Entity-Type Assignment Methods

Entity-type assignments must record the primary semantic derivation method used to produce the assertion.

The canonical initial assignment methods are:

```text
manual
rule
external_mapping
internal_autonomous_agent
external_ai_model
import
```

### 6.6 `manual`

A human explicitly assigns the canonical GNI entity type.

### 6.7 `rule`

A deterministic GNI rule, ruleset, or other reproducible non-AI classification mechanism determines the canonical type.

### 6.8 `external_mapping`

The canonical type is derived through an explicit stored mapping from an external ontology, vocabulary, or classification system to a GNI canonical type.

Examples include mappings from IPTC, Schema.org, or Wikidata.

The fact that software or an AI system executed the mapping does not change the assignment method to an AI method.

### 6.9 `internal_autonomous_agent`

A GNI-controlled autonomous agent derives the entity-type assertion through reasoning, orchestration, tool use, contextual analysis, or other autonomous decision-making.

The agent may invoke models, tools, databases, retrieval systems, or other services as part of its reasoning process.

The assignment method remains `internal_autonomous_agent` when the autonomous GNI agent is responsible for the semantic decision.

### 6.10 `external_ai_model`

An external AI model directly produces the semantic entity-type classification without an autonomous GNI agent independently determining the result.

Examples include direct classification calls to an externally hosted language model or machine-learning inference service.

The external provider, model identifier, model version, request parameters, and related execution details belong in provenance.

### 6.11 `import`

A pre-existing canonical type assertion is imported and adopted without GNI deriving the classification through a rule, external ontology mapping, internal autonomous agent, or external AI model.

`import` describes adoption of the assertion itself. It must not be used merely because the underlying data entered GNI through an import process.

### 6.12 Derivation Rule

The assignment method records the primary semantic derivation path.

```text
Human decision
    → manual

Deterministic GNI logic
    → rule

Explicit external ontology crosswalk
    → external_mapping

Autonomous GNI agent decision
    → internal_autonomous_agent

Direct external AI classification
    → external_ai_model

Imported pre-existing canonical assertion
    → import
```

The actor executing an operation is distinct from the semantic derivation method.

For example:

```text
Internal autonomous agent
    discovers Schema.org type
    applies stored Schema.org → GNI mapping

assignment_method:
    external_mapping

provenance actor:
    internal autonomous agent
```

Likewise:

```text
Internal autonomous agent
    calls external AI model
    evaluates the returned evidence
    independently decides the canonical type

assignment_method:
    internal_autonomous_agent
```

Whereas:

```text
GNI sends classification request
    directly to external AI model
    accepts returned type as classification

assignment_method:
    external_ai_model
```

Supporting actors, models, rules, sources, tools, imported records, and activities belong in provenance and evidence. Their participation does not automatically determine the assignment method.

### 6.13 Reference Table

```text
semantic_assignment_methods

slug
name
description
is_active
metadata
created_at
updated_at
```

### 6.14 GFA-C.4.1 Freeze-Candidate Invariants

```text
✓ An entity may have multiple active canonical type assignments.

✓ Exactly one active entity-type assignment may be primary.

✓ Canonical entity types form a GNI-controlled directed
  acyclic graph.

✓ Entity-type hierarchy edges reject self-edges and cycles.

✓ Entity-type assertions preserve lifecycle history and
  real-world temporal validity as separate facts.

✓ Duplicate active entity/type assignments are prohibited.

✓ External ontology hierarchies are preserved through mappings
  rather than copied blindly into the GNI hierarchy.

✓ entities.entity_type is removed rather than duplicating
  the primary assignment.

✓ Assignment methods are reference-backed.

✓ Initial assignment methods are:

    manual
    rule
    external_mapping
    internal_autonomous_agent
    external_ai_model
    import

✓ Assignment method describes semantic derivation.

✓ Assignment method does not describe transport mechanism.

✓ Assignment method does not by itself identify the actor,
  model, tool, provider, or source.

✓ Detailed actor/model/tool/source information belongs in
  provenance and evidence.
```

### 6.15 GFA-C.4.1 — FREEZE CANDIDATE


## 7. GFA-C.4.2 — External Ontology Mapping Foundation

**Status: FREEZE CANDIDATE**

GNI requires a reusable external semantic mapping foundation capable of representing authoritative external concepts, classes, properties, and identities without embedding third-party identifiers directly into canonical GNI tables.

The external semantic foundation is shared across GNI subsystems.

It must eventually support mappings for:

```text
entity types
entities
events
geographies
points of interest
topics
other controlled concepts
```

External resources are stored once. Individual GNI subsystems reference those resources through strongly typed mapping relationships.

The logical foundation is:

```text
external_semantic_authorities
        │
        ▼
external_semantic_schemes
        │
        ▼
external_semantic_resources
        │
        ├── resource_kind
        │
        ▼
semantic_mapping_relations
        │
        ▼
strongly typed GNI mapping tables
```

Examples of future strongly typed mapping tables include:

```text
entity_type_external_mappings
entity_external_mappings
event_external_mappings
geography_external_mappings
poi_external_mappings
topic_external_mappings
```

GNI does not use a polymorphic `target_type` / `target_id` mapping architecture when doing so would prevent PostgreSQL from enforcing actual foreign-key integrity.

---

### 7.1 External Semantic Authorities

`external_semantic_authorities` represents the organization or semantic authority responsible for one or more external vocabularies, ontologies, knowledge graphs, or concept schemes.

```text
external_semantic_authorities

slug
name
description
authority_uri
is_active
metadata
created_at
updated_at
```

Initial authorities include:

```text
iptc
schema_org
wikidata
w3c
```

An authority is distinct from an individual semantic scheme.

For example, IPTC maintains multiple controlled vocabularies. GNI must therefore represent IPTC once as an authority while separately representing individual IPTC schemes.

---

### 7.2 External Semantic Schemes

`external_semantic_schemes` represents an individual ontology, controlled vocabulary, knowledge graph namespace, or semantic concept scheme.

```text
external_semantic_schemes

id
authority_slug
slug
name
scheme_uri
preferred_prefix
version_label
version_date
last_retrieved_at
is_active
metadata
created_at
updated_at
```

Relationships:

```text
authority_slug
    FK → external_semantic_authorities.slug
```

Examples include:

```text
iptc_cpnature
schema_org
wikidata
skos
```

Possible initial mappings:

```text
iptc_cpnature
    authority → iptc
    preferred_prefix → cpnat

schema_org
    authority → schema_org
    preferred_prefix → schema

wikidata
    authority → wikidata
    preferred_prefix → wd

skos
    authority → w3c
    preferred_prefix → skos
```

External schemes do not share a universal versioning model.

`version_label` and `version_date` are therefore nullable.

Some external schemes publish formal releases. Others evolve continuously.

`last_retrieved_at` records when GNI most recently retrieved or verified information from the external scheme.

---

### 7.3 External Semantic Resource Kinds

External semantic resources are not limited to classes or named concepts.

GNI must also be capable of preserving external predicates and individual identities.

The canonical reference table is:

```text
external_semantic_resource_kinds

slug
name
description
is_active
metadata
created_at
updated_at
```

The initial resource kinds are:

```text
concept
class
property
individual
other
```

Examples:

```text
IPTC cpnat:organisation
    → concept

Schema.org GovernmentOrganization
    → class

Schema.org birthPlace
    → property

Wikidata QID representing a class
    → class

Wikidata QID representing a specific real-world thing
    → individual

Wikidata P19
    → property
```

`resource_kind` describes the semantic role of the external resource within its native system.

It must not be inferred solely from identifier syntax.

---

### 7.4 External Semantic Resources

`external_semantic_resources` stores an external semantic resource exactly once for each external scheme.

```text
external_semantic_resources

id
scheme_id
resource_kind
external_identifier
external_uri
name
description
source_created_at
source_modified_at
source_retired_at
is_active
metadata
first_retrieved_at
last_retrieved_at
created_at
updated_at
```

Relationships:

```text
scheme_id
    FK → external_semantic_schemes.id

resource_kind
    FK → external_semantic_resource_kinds.slug
```

Required uniqueness:

```text
UNIQUE (
    scheme_id,
    external_identifier
)

UNIQUE (
    id,
    resource_kind
)
```

Where an authoritative URI exists, GNI should also prevent duplicate active representation of the same URI.

The `(id, resource_kind)` key supports composite foreign keys from
strongly typed mapping tables. It allows PostgreSQL to verify that a
mapping edge references an external resource of the required semantic
kind.

External identifiers retain their exact native representation.

Examples:

```text
cpnat:organisation
cpnat:animal
GovernmentOrganization
birthPlace
Qxxxxxx
P19
```

GNI must not destructively normalize external identifiers into lowercase, `snake_case`, or any other internal naming convention.

For example:

```text
External:
GovernmentOrganization

GNI:
government_organization
```

These are different identifiers belonging to different semantic systems.

Their relationship is represented explicitly.

---

### 7.5 External Identifier and URI Separation

`external_identifier` and `external_uri` represent different facts.

For example:

```text
external_identifier:
cpnat:person

external_uri:
http://cv.iptc.org/newscodes/cpnature/person
```

Likewise:

```text
external_identifier:
GovernmentOrganization

external_uri:
https://schema.org/GovernmentOrganization
```

And:

```text
external_identifier:
Qxxxxxx

external_uri:
http://www.wikidata.org/entity/Qxxxxxx
```

GNI preserves both where available.

A URI must never be reconstructed from an identifier unless the external scheme formally guarantees that transformation.

---

### 7.6 Semantic Mapping Relations

External mappings must explicitly state the semantic relationship between the canonical GNI resource and the external resource.

The canonical reference table is:

```text
semantic_mapping_relations

slug
name
relation_family
applicable_resource_kind
external_identifier
external_uri
description
is_symmetric
is_transitive
inverse_slug
is_active
metadata
created_at
updated_at
```

`applicable_resource_kind` is a foreign key to
`external_semantic_resource_kinds.slug`.

Required uniqueness includes:

```text
UNIQUE (
    slug,
    applicable_resource_kind
)
```

This composite key supports database-enforced semantic-kind
compatibility in strongly typed mapping tables.

The initial mapping relations are:

Concept mappings — SKOS
```text
exact_match
close_match
broad_match
narrow_match
related_match
```

Class mappings — OWL/RDFS
```text
equivalent_class
subclass_of
superclass_of
```

Property mappings — OWL/RDFS
```text
equivalent_property
subproperty_of
superproperty_of
```

Individual identity — OWL
```text
same_as
```

These correspond to W3C SKOS mapping semantics:

```text
exact_match
    → skos:exactMatch

close_match
    → skos:closeMatch

broad_match
    → skos:broadMatch

narrow_match
    → skos:narrowMatch

related_match
    → skos:relatedMatch
```

Relationship characteristics:

```text
exact_match
    symmetric  = true
    transitive = true
    inverse    = exact_match

close_match
    symmetric  = true
    transitive = false
    inverse    = close_match

broad_match
    symmetric  = false
    transitive = false
    inverse    = narrow_match

narrow_match
    symmetric  = false
    transitive = false
    inverse    = broad_match

related_match
    symmetric  = true
    transitive = false
    inverse    = related_match
```

The relation family and applicable resource kind are:

```text
exact_match          skos    concept
equivalent_class     owl     class
subclass_of          rdfs    class
equivalent_property  owl     property
subproperty_of       rdfs    property
same_as              owl     individual
```

That prevents invalid combinations such as:

```text
birthPlace
    exact_match
some property
```

External mapping equivalence is never assumed merely because labels appear similar.

---

### 7.7 Mapping Direction

All GNI external semantic mappings use a fixed semantic direction.

```text
SUBJECT
    = canonical GNI resource

OBJECT
    = external semantic resource
```

For example:

```text
GNI government_organization
    exact_match
Schema.org GovernmentOrganization
```

For hierarchical mapping:

```text
GNI government_agency
    broad_match
Schema.org GovernmentOrganization
```

means:

```text
Schema.org GovernmentOrganization
is broader than
GNI government_agency
```

The meaning of a mapping relation must never depend on table column ordering or developer interpretation.

The mapping direction is always:

```text
GNI → EXTERNAL
```

---

### 7.8 Entity-Type External Mappings

The first consumer of the external semantic foundation is the canonical entity-type system.

```text
entity_type_external_mappings

id
entity_type_id
external_resource_id
mapping_relation
resource_kind
confidence
evidence
provenance
valid_from
valid_to
is_active
superseded_at
created_at
updated_at
```

Relationships:

```text
entity_type_id
    FK → entity_types.id

external_resource_id
    FK → external_semantic_resources.id

mapping_relation
    FK → semantic_mapping_relations.slug

(external_resource_id, resource_kind)
    composite FK →
    external_semantic_resources(id, resource_kind)

(mapping_relation, resource_kind)
    composite FK →
    semantic_mapping_relations(
        slug,
        applicable_resource_kind
    )
```

An active mapping uniquely represents the semantic relationship between one GNI entity type and one external semantic resource.

Entity-type mappings require:

```text
resource_kind = class
    or
resource_kind = concept
```

The selected mapping relation must be applicable to the same resource
kind. This compatibility is enforced by composite foreign keys rather
than service convention alone.

The same pair must not simultaneously have contradictory active mappings.

Required active uniqueness is therefore:

```text
UNIQUE (
    entity_type_id,
    external_resource_id
)
WHERE is_active
```

For example, GNI must not simultaneously assert:

```text
government_agency
    exact_match
GovernmentOrganization
```

and:

```text
government_agency
    broad_match
GovernmentOrganization
```

If the semantic interpretation changes, the previous mapping is superseded and retained historically rather than destructively overwritten.

---

### 7.9 Mapping Confidence

`confidence` may be used where a mapping was inferred or remains uncertain.

```text
confidence
    numeric(5,4)
    NULL allowed
```

Where supplied:

```text
0 <= confidence <= 1
```

`NULL` means no meaningful confidence value was supplied or calculated.

It must not automatically be converted to `1.0000`.

An authoritative curated mapping may therefore legitimately have:

```text
confidence = NULL
```

while an AI-assisted candidate mapping may have:

```text
confidence = 0.9432
```

Mapping confidence does not replace the semantic relationship expressed by `mapping_relation`.

---

### 7.10 Evidence and Provenance

External semantic mappings must support evidence and provenance.

```text
evidence
provenance
```

may initially use JSONB where a more specialized provenance architecture has not yet been established.

Evidence may describe why the mapping is believed to be semantically correct.

Provenance may identify:

```text
source
retrieval activity
human reviewer
rule
internal autonomous agent
external AI model
source dataset
external release
verification date
```

Provenance describes the origin and processing history of the assertion.

It does not replace the mapping relationship itself.

---

### 7.11 External Resource Reuse

External semantic resources are shared.

For example, one Wikidata class record is stored once:

```text
external_semantic_resources
    Wikidata Qxxxxxx
```

Multiple GNI resources may then map to it where semantically appropriate.

The external resource itself is never duplicated merely because it participates in multiple mappings.

Likewise, a Schema.org property such as `birthPlace` may later be used when defining or mapping geography relationship semantics without creating another Schema.org `birthPlace` record.

---

### 7.12 Strongly Typed Mapping Tables

GNI deliberately uses strongly typed mapping-edge tables.

Preferred architecture:

```text
external_semantic_resources
        │
        ├── entity_type_external_mappings
        ├── entity_external_mappings
        ├── geography_external_mappings
        ├── event_external_mappings
        ├── poi_external_mappings
        └── topic_external_mappings
```

Rejected architecture:

```text
external_mappings

target_type
target_id
external_resource_id
```

The rejected polymorphic design prevents PostgreSQL from enforcing a normal foreign key from `target_id` to the correct canonical table.

GNI favors relational integrity over superficial reduction in table count.

---

### 7.13 External Standards Are Mutable

External standards are authoritative but not static.

GNI must support:

```text
new external concepts
modified concepts
deprecated concepts
retired concepts
new releases
changed mappings
superseded mappings
```

without destructive deletion of historical semantic information.

External resource lifecycle fields include:

```text
source_created_at
source_modified_at
source_retired_at
first_retrieved_at
last_retrieved_at
is_active
```

GNI lifecycle metadata and external-source lifecycle metadata represent different facts and must remain distinct.

---

### 7.14 GFA-C.4.2 Freeze-Candidate Invariants

```text
✓ External semantic authorities are represented independently
  from the schemes they maintain.

✓ External semantic schemes preserve authoritative scheme
  identity, URI, preferred prefix, available version
  information, and retrieval metadata.

✓ External semantic resources are stored once per external
  scheme and identifier.

✓ External resources preserve exact native identifier syntax,
  spelling, capitalization, QCodes, QIDs, property IDs,
  and authoritative URIs.

✓ External resource kinds are reference-backed.

✓ Initial external resource kinds are:

    concept
    class
    property
    individual
    other

✓ External resource kind is not inferred solely from
  identifier syntax.

✓ GNI canonical identifiers and external identifiers remain
  separate semantic identities.

✓ GNI never reconstructs external identifiers from GNI slugs.

✓ External URIs are preserved separately from external
  identifiers.

✓ Semantic mapping relationships are reference-backed and
  record both relation family and applicable resource kind.

✓ Initial mapping relationships are:

    exact_match
    close_match
    broad_match
    narrow_match
    related_match
    equivalent_class
    subclass_of
    superclass_of
    equivalent_property
    subproperty_of
    superproperty_of
    same_as

✓ Mapping tables enforce compatibility between external
  resource kind and mapping-relation applicability.

✓ Mapping direction is always:

    GNI canonical resource → external semantic resource

✓ broad_match therefore means the external resource is
  broader than the GNI canonical resource.

✓ External resources are reusable across GNI subsystems.

✓ Strongly typed mapping-edge tables are used instead of
  polymorphic target_type / target_id references.

✓ Mapping history is preserved through lifecycle and
  supersession instead of destructive replacement.

✓ Mapping confidence may be NULL.

✓ Evidence and provenance remain distinct from the
  semantic mapping relationship.

✓ External standards are treated as evolving authorities,
  not immutable constants.
```

### 7.15 GFA-C.4.2 — FREEZE CANDIDATE


## 8. GFA-C.4.3 — Entity ↔ Geography Foundation

**Status: FROZEN**

GFA-C.3 established that geography remains a separate first-class GNI
subsystem and that entities reference canonical geography records
through explicit relationships.

The existing free-text field:

```text
entities.country_or_jurisdiction
```

is not part of the canonical entity architecture. It is not replaced by
a single `entities.geography_id`, because an entity may have multiple
geographically meaningful relationships with different semantics.

The canonical architecture is:

```text
entity_geography_relationship_types
                │
                ▼
        entity_geographies
                │
                ▼
            geographies
```

### 8.1 Removal of `country_or_jurisdiction`

`entities.country_or_jurisdiction` collapses facts such as:

```text
National Election Commission
    jurisdiction_in → South Korea

Samsung Electronics
    headquartered_in → South Korea

U.S. Forces Korea
    based_in → South Korea
```

into one ambiguous string.

Because GFA-C.1 found no persisted production entity records, no
production values currently require semantic migration. The migration
must nevertheless repeat that preflight and refuse destructive cleanup
if unmapped rows have appeared.

The legacy column may remain only during the additive compatibility
window. GFA-C.6 removes it after all repository consumers and fixtures
have migrated.

### 8.2 Relationship-Type Vocabulary

```text
entity_geography_relationship_types

slug
name
description
is_active
metadata
created_at
updated_at
```

`slug` is the stable lowercase `snake_case` primary key.

Illustrative types include:

```text
located_in
headquartered_in
based_in
jurisdiction_in
operates_in
incorporated_in
founded_in
born_in
resident_in
citizen_of
```

These examples do not freeze the authoritative initial vocabulary.
GFA-C.5 establishes relationship definitions, allowed entity-type
domains, geography-range policies, and any cardinality policy.

The foundation permits multiple simultaneous values for a relationship
type. Duplicate-fact prevention must not be interpreted as a universal
single-value constraint.

### 8.3 Entity-Geography Assertions

```text
entity_geographies

id
entity_id
geography_id
relationship_type
assignment_method
confidence
evidence
provenance
valid_from
valid_to
is_active
superseded_at
created_at
updated_at
```

Relationships:

```text
entity_id
    FK → entities.id
    ON DELETE RESTRICT

geography_id
    FK → geographies.id
    ON DELETE RESTRICT

relationship_type
    FK → entity_geography_relationship_types.slug
    ON DELETE RESTRICT

assignment_method
    FK → semantic_assignment_methods.slug
    ON DELETE RESTRICT
```

Checks:

```text
confidence IS NULL
    OR 0 <= confidence <= 1

valid_to IS NULL
    OR valid_from IS NULL
    OR valid_to >= valid_from
```

Required partial uniqueness:

```text
UNIQUE (
    entity_id,
    geography_id,
    relationship_type
)
WHERE is_active
```

Supporting indexes:

```text
(entity_id, is_active)
(geography_id, is_active)
(relationship_type, is_active)
(valid_from, valid_to)
```

### 8.4 Lifecycle and Temporal Validity

`is_active` records assertion lifecycle. It means that an assertion has
not been retired or superseded.

`valid_from` and `valid_to` record real-world temporal applicability.

An active assertion may legitimately describe a past or scheduled
future interval. Current real-world validity is therefore evaluated
from the validity interval, not from `is_active` alone.

Historical assertions are retained rather than destructively
overwritten.

### 8.5 Geography Reuse and Hierarchy

Canonical geography records are reused. An entity relationship never
copies or redefines a geography.

Geographic containment remains owned by the geography subsystem.

```text
Entity
    located_in → Seoul
```

does not automatically create:

```text
Entity
    located_in → South Korea
```

merely because South Korea is an ancestor of Seoul. A broader
entity-geography row exists only when it represents an independently
asserted semantic fact.

### 8.6 Assignment Method, Confidence, and Provenance

Entity-geography assertions reuse the semantic assignment methods
established in GFA-C.4.1.

The assignment method records semantic derivation rather than actor
identity or transport mechanism. Evidence and provenance remain
separate supporting facts.

Multiple sources supporting the same fact belong in evidence and
provenance rather than duplicate active assertion rows.

The service stores supporting information in append-only structured
collections:

```json
{
  "supporting_evidence": [
    {
      "source": "source-a",
      "document": "document-a"
    },
    {
      "source": "source-b",
      "document": "document-b"
    }
  ]
}
```

and:

```json
{
  "provenance_records": [
    {
      "actor": "operator-a",
      "activity": "manual-review"
    },
    {
      "actor": "agent-b",
      "activity": "external-mapping"
    }
  ]
}
```

When a duplicate active fact is rediscovered, the service locks the
existing row and appends distinct incoming evidence and provenance
records. Identical records are not appended twice. Empty incoming
support does not change the stored collections.

If a pre-existing row contains an unstructured non-empty JSON object,
that object is preserved as the first record when the structured
collection is created. Supporting information must never be silently
discarded.

`confidence` is `numeric(5,4)`, permits `NULL`, and is constrained to
the inclusive range zero through one when supplied.

### 8.7 Relationship Types as Semantic Properties

An entity-geography relationship type is a semantic property connecting
an entity to a geography. Its external mappings therefore reference
external resources whose:

```text
resource_kind = property
```

Valid mapping relations are property relations:

```text
equivalent_property
subproperty_of
superproperty_of
```

SKOS concept relations such as `exact_match` are not used to map
properties.

Property-kind compatibility does not by itself establish semantic
equivalence. Domain, range, and meaning must also be reviewed during
GFA-C.5 curation.

### 8.8 Relationship-Type External Mappings

```text
entity_geography_relationship_type_external_mappings

id
relationship_type
external_resource_id
mapping_relation
resource_kind
confidence
evidence
provenance
valid_from
valid_to
is_active
superseded_at
created_at
updated_at
```

Relationships:

```text
relationship_type
    FK → entity_geography_relationship_types.slug

(external_resource_id, resource_kind)
    composite FK →
    external_semantic_resources(id, resource_kind)

(mapping_relation, resource_kind)
    composite FK →
    semantic_mapping_relations(
        slug,
        applicable_resource_kind
    )
```

Required check:

```text
resource_kind = property
```

Required active uniqueness:

```text
UNIQUE (
    relationship_type,
    external_resource_id
)
WHERE is_active
```

This prevents simultaneously active contradictory relations between
the same GNI relationship type and external property. A changed
interpretation supersedes the prior mapping and creates a historical
replacement row.

Mapping direction remains:

```text
GNI canonical relationship type
    →
external semantic property
```

External properties remain stored once in
`external_semantic_resources` and are reused across subsystems.

### 8.9 GFA-C.4.3 Frozen Invariants

```text
✓ entities.country_or_jurisdiction is removed from the final
  canonical entity model.

✓ It is not replaced by a single entities.geography_id.

✓ Entity-geography facts are explicit typed assertions.

✓ Assertions reference canonical entities, geographies,
  relationship types, and assignment methods.

✓ Duplicate active facts are prohibited for the same entity,
  geography, and relationship type.

✓ Duplicate prevention does not impose universal single-value
  cardinality on a relationship type.

✓ Assertion lifecycle and real-world validity are distinct.

✓ Historical assertions are retained.

✓ Geography hierarchy remains owned by the geography subsystem.

✓ Geography ancestors are not materialized automatically as
  entity-geography assertions.

✓ Relationship types are semantic properties.

✓ External property mappings are database-enforced as property
  resources using property-applicable mapping relations.

✓ One GNI relationship type/external property pair has at most
  one active mapping relation.

✓ Duplicate discoveries accumulate distinct supporting evidence
  and provenance without creating duplicate fact rows.

✓ Domain, range, meaning, and relationship-specific cardinality
  are curated in GFA-C.5.

✓ Mapping direction is always GNI → external.
```

### 8.10 GFA-C.4.3 — FROZEN


## 9. GFA-C.5 — Standards-Derived Seed Vocabulary

**Status: FROZEN**

GFA-C.5 supplies the first usable canonical vocabulary for the schema
frozen in GFA-C.4.1 through GFA-C.4.3. It seeds stable GNI identifiers
and explicit external mappings; it does not copy an external ontology
wholesale.

The seed is global rather than deployment-specific. Coverage profiles
may later enable a subset without changing the canonical vocabulary.

### 9.1 Curation Rules

The seed follows these rules:

```text
IPTC Concept Nature
    defines the fundamental news-domain entity boundary

Schema.org
    supplies practical class and property mappings where defensible

Wikidata
    is registered for later deep-class and identity mappings

W3C SKOS / OWL / RDFS
    define mapping semantics
```

A type or relationship may remain externally unmapped. Absence of a
defensible mapping is preferable to invented equivalence.

Canonical types represent reusable semantic classes, not industries,
topics, editorial labels, source types, geographies, events, or points
of interest.

### 9.2 Initial Canonical Entity Types

The initial seed contains 32 types:

```text
person
organization
animal
object
other

government_organization
legislature
court
election_authority
military
law_enforcement

company
political_party
international_organization
non_governmental_organization
university
think_tank
labor_union
news_media_organization

facility
legal_instrument
court_case
treaty
technology_product
software
ai_model
weapon_system
vehicle
aircraft
vessel
spacecraft
program_initiative
```

`other` is a controlled fallback. It must not be used when a more
specific active canonical type is known.

`facility` identifies a persistent real-world facility. It does not
replace canonical geography and does not make `point_of_interest` an
entity type.

The following remain outside `entity_types`:

```text
geography          → geographies
event              → events
point of interest  → points_of_interest
abstract concept   → controlled-concept subsystem, generally topics
```

### 9.3 Initial Entity-Type DAG

The initial directed acyclic graph contains these edges:

```text
organization
├── government_organization
│   ├── legislature
│   ├── court
│   ├── election_authority
│   ├── military
│   └── law_enforcement
├── company
├── political_party
├── international_organization
├── non_governmental_organization
├── university
├── think_tank
├── labor_union
└── news_media_organization

object
├── facility
├── legal_instrument
│   └── treaty
├── court_case
├── technology_product
│   ├── software
│   │   └── ai_model
│   └── weapon_system
├── vehicle
│   ├── aircraft
│   ├── vessel
│   └── spacecraft
└── program_initiative
```

`person`, `animal`, and `other` are additional roots. The graph may
gain reviewed edges later; consumers must not assume a single parent.

### 9.4 Initial Entity-Geography Relationship Types

The initial seed contains:

```text
located_in
headquartered_in
based_in
jurisdiction_in
operates_in
incorporated_in
founded_in
born_in
resident_in
citizen_of
```

Curated domains are stored in relationship metadata:

| Relationship | Initial canonical domain |
|---|---|
| `located_in` | `object`, `organization` |
| `headquartered_in` | `organization` |
| `based_in` | `organization`, `person` |
| `jurisdiction_in` | `government_organization`, `legal_instrument`, `court_case` |
| `operates_in` | `organization` |
| `incorporated_in` | `organization` |
| `founded_in` | `organization` |
| `born_in` | `person` |
| `resident_in` | `person` |
| `citizen_of` | `person` |

Domains include descendants of the listed types. Every range is a
canonical geography.

The seed deliberately records many-valued cardinality. It does not
impose a universal one-geography limit: headquarters, residence,
citizenship, operations, and other facts can legitimately be plural or
historical. Tighter rules require a separately reviewed relationship
policy.

### 9.5 Seeded External Authorities and Schemes

The following authorities are seeded:

```text
iptc
schema_org
wikidata
w3c
```

The following schemes are seeded:

| Scheme | Authority | Prefix | Authoritative namespace |
|---|---|---|---|
| `iptc_cpnature` | `iptc` | `cpnat` | `http://cv.iptc.org/newscodes/cpnature/` |
| `schema_org` | `schema_org` | `schema` | `https://schema.org/` |
| `wikidata` | `wikidata` | `wd` | `http://www.wikidata.org/entity/` |
| `skos` | `w3c` | `skos` | `http://www.w3.org/2004/02/skos/core#` |

Schema.org seed data records version 30.0, dated 2026-03-19. Schemes
without a compatible release model retain nullable version fields and
record retrieval time separately.

### 9.6 Fundamental IPTC Mappings

The fundamental Concept Nature resources retain their native QCodes:

```text
person        exact_match  cpnat:person
organization  exact_match  cpnat:organisation
animal        exact_match  cpnat:animal
object        exact_match  cpnat:object
```

These are concept mappings and therefore use SKOS `exact_match`.

IPTC `geoArea`, `event`, `poi`, and `abstract` are not mapped to entity
types because their GNI subsystem boundaries were frozen in GFA-C.3.

### 9.7 Schema.org Class Mappings

The initial mapping set is intentionally conservative.

Equivalent-class mappings include:

```text
organization                   → Organization
government_organization        → GovernmentOrganization
political_party                → PoliticalParty
non_governmental_organization  → NGO
labor_union                    → WorkersUnion
news_media_organization        → NewsMediaOrganization
vehicle                        → Vehicle
```

Reviewed hierarchical mappings include:

```text
person                         subclass_of    Person
object                         subclass_of    Thing
legislature                    subclass_of    GovernmentOrganization
court                          subclass_of    GovernmentOrganization
election_authority             subclass_of    GovernmentOrganization
military                       subclass_of    GovernmentOrganization
law_enforcement                subclass_of    GovernmentOrganization
company                        superclass_of  Corporation
international_organization     subclass_of    Organization
think_tank                     subclass_of    ResearchOrganization
university                     subclass_of    CollegeOrUniversity
facility                       subclass_of    Place
legal_instrument               superclass_of  Legislation
technology_product             subclass_of    Product
software                       superclass_of  SoftwareApplication
aircraft                       subclass_of    Vehicle
vessel                         subclass_of    Vehicle
spacecraft                     subclass_of    Vehicle
```

`superclass_of` is used where the GNI class intentionally covers more
than the external Schema.org class. Mapping direction remains GNI to
external.

No initial Wikidata QID mapping is seeded merely from a label match.
Wikidata mappings require individual QID review.

### 9.8 Schema.org Property Mappings

The following mappings are seeded:

```text
located_in       subproperty_of       location
headquartered_in subproperty_of       location
based_in         subproperty_of       location
founded_in       subproperty_of       foundingLocation
born_in          subproperty_of       birthPlace
```

Every seeded GNI property is narrower than its Schema.org counterpart
because GNI requires a canonical-geography range and curates a more
specific domain. Equivalence would therefore overstate the property
extension.

No initial mapping is asserted for:

```text
jurisdiction_in
operates_in
incorporated_in
resident_in
citizen_of
```

Candidate Schema.org properties for those relationships either have
different domains/ranges or do not preserve the same meaning.
Schema.org `nationality`, for example, is not assumed to be universally
identical to legal citizenship. Silent approximation is prohibited.

### 9.9 Seed Provenance and Evolution

Every GFA-C.5 reference row carries:

```json
{"seed_set": "gfa_c_5"}
```

Seeded mapping assertions additionally identify the reviewed seed set
and review date in provenance.

External vocabulary evolution does not mutate GNI meaning
automatically. A mapping change must supersede the prior active mapping
and preserve its history.

### 9.10 GFA-C.5 Frozen Invariants

```text
✓ The initial entity-type vocabulary is global and database-backed.

✓ The initial hierarchy is a DAG and does not assume one parent.

✓ Geography, event, POI, and abstract-concept boundaries remain intact.

✓ Relationship domains and geography range are explicitly curated.

✓ Relationship cardinality remains many-valued unless separately frozen.

✓ IPTC fundamental identifiers retain native QCode spelling.

✓ Schema.org identifiers retain native spelling and capitalization.

✓ Concept, class, and property mappings use compatible relation kinds.

✓ Mapping direction remains GNI canonical resource → external resource.

✓ Hierarchical mappings do not masquerade as equivalence.

✓ Uncertain external mappings remain absent rather than being invented.

✓ Wikidata is registered but QIDs require individual review.

✓ Seed provenance is explicit and queryable.
```

### 9.11 Formal Freeze Review

The formal review examined:

```text
canonical entity/concept subsystem boundaries
entity-type coverage and hierarchy direction
relationship meaning, domains, range, and cardinality
native external identifier preservation
mapping relation strength and direction
resource-kind compatibility
absence of invented mappings
seed provenance
migration reversibility
direct tests and verification SQL
```

The review identified and corrected semantic overstatement before
freeze:

```text
GNI person
    subclass_of Schema.org Person
    because Schema.org also includes fictional persons

GNI university
    subclass_of Schema.org CollegeOrUniversity
    because the external class is broader

GNI geography properties
    subproperty_of corresponding Schema.org properties
    because GNI requires canonical geography and narrower domains
```

Final verification:

```text
32 seeded entity types
27 seeded DAG edges
10 seeded entity-geography relationship types
23 seeded external resources
29 seeded entity-type mappings
5 seeded relationship-property mappings
0 entity-boundary leaks
0 invented uncertain property mappings
0 incompatible mapping kinds
0 contradictory active mappings
107 repository tests passed
independent downgrade and re-upgrade passed
```

No GFA-C.5 freeze blockers remain.

### 9.12 GFA-C.5 — FROZEN

## 10. GFA-C.6 — Migration, Tests, and Verification

**Status:** FROZEN

### 10.1 Scope

GFA-C.6 closes the temporary compatibility window retained by
GFA-C.4. It migrates the last repository fixtures to the normalized
model and removes:

```text
entities.entity_type
entities.country_or_jurisdiction
ix_entities_type_active
ix_entities_country_or_jurisdiction
```

No GFA-C.4.4 is introduced. Type and geography meaning remain owned by
the frozen GFA-C.4.1 and GFA-C.4.3 assertion models.

### 10.2 Consumer and Data Preflight

Repository-wide inspection found:

```text
production reads of either legacy field                    0
production writes of either legacy field                   0
test fixtures writing entities.entity_type                 2
test fixtures writing country_or_jurisdiction              1
persisted rows in the original GFA-C.1 inventory           0
```

The affected fixtures used the strings only to satisfy the old ORM
constructor. Their behavior depends on entity aliases or normalized
type/geography assertions, so removing those arguments loses no test
meaning.

The final repository drift audit also found a pre-existing GFA-A ORM
declaration for a redundant single-column
`documents.ingestion_format` index that no migration created. The
implemented schema already has
`ix_documents_ingestion_format_published_at`, whose leading column
supports the same lookup prefix. Removing the stale `index=True`
declaration aligns metadata with the frozen schema without changing
database DDL.

### 10.3 Guarded Migration Policy

Revision `d62e9f3a5b01` repeats the inventory assumption before any
destructive DDL:

```text
if entities contains zero rows
    remove the legacy indexes and columns
else
    abort the migration transaction
```

Any row is treated as unmapped. This conservative rule is necessary
because `entity_type` is required on the legacy schema and
`country_or_jurisdiction` does not identify whether it means
headquarters, jurisdiction, operation, residence, citizenship, or
another relationship. Automatically translating either value would
invent semantics, temporal scope, evidence, or provenance.

An operator encountering the guard must first apply a separately
reviewed, provenance-preserving migration or explicitly remove the
unexpected rows. GFA-C.6 never drops or guesses their meaning.

The downgrade uses the same empty-table guard. On an empty table it
restores the exact legacy columns, nullability, and indexes. It refuses
to fabricate a required legacy type for entities created after
upgrade.

### 10.4 Model and Fixture Migration

The `Entity` ORM now contains identity and lifecycle fields only:

```text
id
canonical_name
canonical_name_native
is_active
metadata
created_at
updated_at
```

Entity type is assigned through `entity_type_assignments`.
Entity-geography facts are asserted through `entity_geographies`.
The alias-classification and semantic-service fixtures create entity
identity first and use their actual normalized or alias dependencies.

### 10.5 Direct Tests

Three C.6-specific tests prove:

```text
the migration guard rejects an unexpected entity row
the Entity ORM exposes neither legacy column
the Entity ORM exposes neither legacy index
PostgreSQL exposes neither legacy column at migration head
PostgreSQL exposes neither legacy index at migration head
```

The focused affected suite passed 18 tests, including entity alias
classification, normalized type assignment, entity-geography
assertions, evidence accumulation, temporal constraints, and the
absence of inferred geography ancestors.

### 10.6 Verification

Validation used a fresh isolated PostgreSQL 17.10 cluster.

```text
full history through GFA-C.5                              passed
upgrade with one unexpected legacy entity                 rejected
clean GFA-C.6 upgrade                                     passed
legacy columns after upgrade                                   0
legacy indexes after upgrade                                   0
GFA-C verification SQL                                   passed
guarded downgrade to GFA-C.5                             passed
re-upgrade to GFA-C.6                                    passed
focused affected tests                               18 passed
complete repository suite                           110 passed
schema-only snapshot regenerated                         yes
Alembic model/schema drift operations                       0
```

### 10.7 Formal Freeze Review

The formal review examined:

```text
consumer and fixture migration completeness
repeatability of the zero-row preflight assumption
failure behavior with unexpected entity data
transactional destructive DDL ordering
downgrade fidelity and its no-fabrication guard
ORM and physical-schema agreement
legacy column and index absence
normalized assertion continuity
verification SQL coverage
focused and repository-wide regression results
documentation and schema-snapshot consistency
```

One documentation-only blocker was found during review: the narrative
focused-test count remained at 17 after the direct guard test raised
the final count to 18. The count was corrected to match the executed
test result. No code, data-safety, schema, or semantic blocker was
found.

The destructive boundary is explicit and fails closed. No legacy
value is silently lost, guessed, or copied into a semantically
stronger assertion. The migration cannot proceed outside the reviewed
zero-row inventory without a separate approved remediation.

No GFA-C.6 freeze blockers remain.

### 10.8 GFA-C.6 — FROZEN

## 11. Frozen Invariants

The completed GFA-C foundation freezes the following invariants:

```text
entities represent canonical real-world identity, not abstract topics
geographies, events, POIs, and abstract concepts remain separate
entity types are canonical reference rows arranged as a DAG
entity type is asserted through entity_type_assignments
entity-geography meaning is an explicit typed relationship
entity-geography assertions remain many-valued unless separately constrained
no geography-ancestor assertion is inferred automatically
assertions preserve lifecycle separately from real-world validity
confidence and validity intervals are database constrained
duplicate discovery accumulates distinct evidence and provenance
external resources and mapping relations are kind compatible
one canonical/external pair has at most one active mapping relation
uncertain standards mappings remain absent rather than invented
mapping direction is GNI canonical resource to external resource
entities contain no free-text type or jurisdiction compatibility field
unexpected legacy entity rows block destructive compatibility cleanup
```

These invariants may be extended only through a separately reviewed
post-GFA-C change. They must not be weakened through fixture
shortcuts, implicit inference, untyped metadata, or compatibility
columns.

## 12. Verification Results

The final frozen implementation at Alembic revision
`d62e9f3a5b01` was verified on 2026-07-26 against isolated PostgreSQL
17.10:

```text
GFA-C semantic foundation tables                            13
seeded entity types                                         32
seeded hierarchy edges                                      27
seeded entity-geography relationship types                  10
seeded external semantic resources                          23
seeded entity-type mappings                                 29
seeded relationship-property mappings                        5
legacy entity semantic columns                               0
legacy entity semantic indexes                               0
invalid or contradictory active mappings                     0
invalid confidence or validity assertions                    0
entity-boundary leaks                                        0
invented uncertain property mappings                         0
focused GFA-C.6 and affected-consumer tests                  18
complete repository tests                                  110
Alembic model/schema drift operations                        0
```

The unexpected-row guard rejected destructive cleanup as designed.
The clean upgrade, guarded downgrade, re-upgrade, complete GFA-C
verification SQL, and regenerated schema-only snapshot all passed.

**GFA-C — FROZEN**
