# AI Routing Technical Specification

**Project:** Global News Intelligence Platform  
**Document:** `AI_ROUTING_TECHNICAL_SPECIFICATION.md`  
**Status:** Development Placeholder / Architectural Seed  
**Version:** 0.1-placeholder

---

## 1. Purpose

This document reserves the detailed architecture for provider-agnostic AI task routing, local-first inference, OpenAI escalation, structured outputs, budgets, observability, evaluation, and failure handling.

---

## 2. Architectural Invariants

- Application services must not call a specific LLM provider directly.
- All generative/model requests pass through the LLM Router or a specialized model service abstraction.
- Local inference is preferred when quality and latency are adequate.
- OpenAI is an escalation layer, not the default path for routine bulk processing.
- Original source content must remain separate from generated output.
- Every AI result must retain model/provider provenance.
- Structured tasks must validate output against schemas before persistence.
- Budget controls must be enforceable before dispatch.

---

## 3. Task Classes

Potential tasks:

```text
classification
entity_extraction
entity_resolution
translation
summarization
future_event_detection
temporal_reasoning
claim_extraction
novelty_detection
story_comparison
calendar_validation
research_reasoning
question_answering
```

Embedding and ASR may use the same provider abstraction principles even when implemented by dedicated services.

---

## 4. Routing Request Contract

Candidate request metadata:

```text
task
language
source_language
target_language
priority
maximum_cost
maximum_latency
minimum_quality
local_preference
allow_openai
context_length
schema_id
classification_confidence
source_authority
coverage_profile_id
monitoring_priority
story_importance
document_id
story_id
calendar_event_id
calendar_occurrence_id
```

---

## 5. Provider Registry

Potential provider metadata:

```text
provider
model
endpoint
capabilities
languages
context_window
supports_json_schema
supports_tools
cost_input
cost_output
estimated_tokens_per_second
health
priority
```

Pricing must be configuration data, not hard-coded business logic.

---

## 6. Routing Strategy

Conceptual flow:

```text
Task request
    ↓
Deterministic solution available?
    ├── yes → use deterministic path
    └── no
         ↓
Specialized local model available?
    ├── yes → local model
    └── no
         ↓
Local general LLM
         ↓
Confidence / validation gate
    ├── pass → persist
    └── fail / high-value ambiguity
         ↓
OpenAI escalation if policy + budget allow
```

---

## 7. Budgeting

Future design should support:

```text
daily provider budget
monthly provider budget
per-task maximum
per-story maximum
per-calendar-event maximum
priority reservation
soft warning threshold
hard stop threshold
```

Budget exhaustion should degrade gracefully to local-only operation where possible.

---

## 8. Structured Output

Every structured task should use versioned schemas.

Possible records:

```text
ai_jobs
ai_attempts
ai_results
ai_usage
ai_provider_health
ai_schema_versions
```

Failed schema validation should be visible as a first-class failure type.

---

## 9. Provenance

Persist at minimum:

```text
provider
model
model_version when known
prompt/template version
schema version
input hash
output hash
token usage
estimated cost
latency
created_at
retry/escalation chain
```

Do not store sensitive credentials or unnecessary prompt secrets in ordinary logs.

---

## 10. Confidence and Escalation

The later spec should define task-specific confidence policies rather than one global threshold.

Examples:

```text
translation confidence
classification confidence
temporal extraction confidence
entity resolution confidence
novelty confidence
```

Escalation may depend on both model confidence and operational value.

---

## 11. Caching and Idempotency

Potential cache key inputs:

```text
task
normalized input hash
model/policy version
schema version
target language
```

Repeated identical tasks should not generate unnecessary paid calls.

---

## 12. Failure Modes

Explicitly handle:

```text
provider unavailable
rate limit
timeout
invalid JSON
schema mismatch
context overflow
model refusal
low confidence
budget denied
local GPU unavailable
```

Fallback behavior must be task-specific and auditable.

---

## 13. Worker Placeholder

Potential queues:

```text
llm-local
llm-openai
translation
classification
calendar-ai
novelty-ai
research-ai
```

Priority queues may separate real-time alerts from bulk backfills.

---

## 14. Benchmark Placeholder

Benchmark each candidate model/provider on:

```text
accuracy
hallucination rate
schema reliability
translation fidelity
classification F1
entity extraction
reasoning quality
latency
tokens/second
GPU memory
cost per 1,000 tasks
```

Real project content must be used.

---

## 15. Open Decisions

- provider interface implementation,
- exact local models,
- exact OpenAI models by task,
- confidence calibration,
- prompt/template registry,
- local batching strategy,
- vLLM deployment topology,
- paid-call caching policy,
- cost allocation model,
- circuit breaker behavior.
