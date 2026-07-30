from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_attention_score_bands_and_story_floors_are_consistent() -> None:
    attention = _read(
        "docs/specifications/CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md"
    )
    story = _read(
        "docs/specifications/STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md"
    )
    master = _read("docs/specifications/MASTER_TECHNICAL_SPECIFICATION.md")

    for document in (attention, story, master):
        assert "High +0" in document
        assert "Critical +0" in document

    assert "| `0–9` | `Low +0` through `Low +9` |" in attention
    assert "| `10–19` | `Normal +0` through `Normal +9` |" in attention
    assert "| `20–29` | `High +0` through `High +9` |" in attention
    assert "| `30–39` | `Critical +0` through `Critical +9` |" in attention
    assert "| `2–3` | `20` (`High +0`) |" in attention
    assert "| `4+` | `30` (`Critical +0`) |" in attention


def test_one_item_candidate_stories_are_not_persisted() -> None:
    attention = _read(
        "docs/specifications/CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md"
    )
    story = _read(
        "docs/specifications/STORY_INTELLIGENCE_TECHNICAL_SPECIFICATION.md"
    )

    assert "does not persist one-item candidate Stories or candidate clusters" in attention
    assert "One-item candidate Stories" in story
    assert "Story creation requires two qualifying members" in story


def test_attention_priority_domains_remain_separate() -> None:
    attention = _read(
        "docs/specifications/CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md"
    )

    for priority_domain in (
        "source polling priority",
        "Calendar monitoring priority",
        "alert delivery priority",
        "AI job priority",
        "attention score",
    ):
        assert priority_domain in attention

    assert (
        "attention score never overwrites polling, Calendar, alert, or AI-job priority"
        in attention
    )


def test_video_asr_is_operator_requested_and_not_automatic() -> None:
    master = _read("docs/specifications/MASTER_TECHNICAL_SPECIFICATION.md")
    video = _read(
        "docs/specifications/VIDEO_INTELLIGENCE_TECHNICAL_SPECIFICATION.md"
    )
    worker = _read("docs/implementation/WORKER_DESIGN_SPECIFICATION.md")

    assert "ASR is not automatic merely because captions are absent" in master
    assert "Automatic ASR is prohibited" in video
    assert "Opening the Video Processing page creates no worker task" in worker
    assert "invoke local ASR when captions are unavailable" not in master


def test_story_badge_contract_is_shared_by_policy_and_ui() -> None:
    attention = _read(
        "docs/specifications/CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md"
    )
    ui_architecture = _read(
        "docs/architecture/WEB_UI_IMPLEMENTATION_STRATEGY.md"
    )
    ui_notes = _read("docs/implementation/UI_IMPLEMENTATION_NOTES.md")

    for document in (attention, ui_architecture, ui_notes):
        assert "[High] +7 [12]" in document
        assert "priority-driving Story" in document

    assert "Standalone items show no Story count bubble" in ui_architecture
    assert "Standalone items omit the bubble" in ui_notes


def test_new_specs_are_indexed() -> None:
    index = _read("docs/README.md")

    for filename in (
        "CONTENT_ATTENTION_AND_ENRICHMENT_POLICY.md",
        "IDENTITY_PROFILE_AND_PREFERENCE_ARCHITECTURE.md",
        "SEMANTIC_WATCH_TECHNICAL_SPECIFICATION.md",
        "VIDEO_INTELLIGENCE_TECHNICAL_SPECIFICATION.md",
    ):
        assert filename in index
