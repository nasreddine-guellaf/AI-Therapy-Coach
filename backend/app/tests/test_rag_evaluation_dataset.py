"""Static contract tests for the measurable RAG evaluation baseline."""

import json
from collections import Counter
from pathlib import Path


DATASET = (
    Path(__file__).resolve().parents[2]
    / "evaluations"
    / "rag"
    / "dataset.json"
)


def test_rag_dataset_contains_30_well_formed_cases() -> None:
    items = json.loads(DATASET.read_text(encoding="utf-8"))["items"]
    required = {
        "question",
        "expected_behavior",
        "expected_source_ids",
        "type",
        "notes",
    }

    assert len(items) == 30
    assert all(required <= item.keys() for item in items)
    assert all(isinstance(item["expected_source_ids"], list) for item in items)


def test_rag_dataset_covers_every_required_category() -> None:
    items = json.loads(DATASET.read_text(encoding="utf-8"))["items"]
    counts = Counter(item["type"] for item in items)

    assert set(counts) == {
        "answerable",
        "unanswerable",
        "cross_document",
        "multilingual",
        "safety",
    }
    assert all(count > 0 for count in counts.values())

