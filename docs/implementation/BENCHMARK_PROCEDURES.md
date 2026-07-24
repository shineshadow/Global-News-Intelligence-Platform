# Benchmark Procedures

**Project:** Global News Intelligence Platform  
**Document:** `BENCHMARK_PROCEDURES.md`  
**Status:** Placeholder / Evaluation Protocol

---

## Purpose

This document should define reproducible benchmarking for models, classifiers, acquisition methods, clustering, ASR, translation, and AI routing.

---

## Benchmark Dataset Rules

- Preserve a versioned permanent corpus.
- Use real representative project content.
- Include all priority languages and source types.
- Separate train/tuning examples from held-out evaluation examples.
- Record human labels and adjudication notes.
- Never silently change ground truth after model comparison.

---

## Required Benchmark Families

### Classification

```text
topic precision/recall/F1
hierarchical accuracy
multi-geography accuracy
entity extraction/entity resolution
document-type accuracy
confidence calibration
cross-language consistency
```

### Translation

```text
fidelity
names/proper nouns
political terminology
military terminology
legal terminology
omission/addition rate
```

### Story Intelligence

```text
same-story precision/recall
false merge/split
cross-language clustering
new-development precision/recall
```

### Acquisition

```text
fetch success
extraction success
missed-item rate
false-item rate
duplicate rate
resource cost
```

### AI Routing

```text
quality
schema reliability
latency
GPU cost
API cost
escalation rate
```

---

## Benchmark Run Record

Every benchmark should record:

```text
dataset version
code commit
model/provider version
configuration
thresholds
hardware
start/end time
metrics
errors
human notes
recommendation
```
