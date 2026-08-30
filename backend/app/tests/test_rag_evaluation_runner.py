"""Tests for safe, measurable hybrid RAG evaluation reporting."""

from app.domain.interfaces.retriever import RetrievedChunk
from app.scripts.evaluate_rag import category_scores, score_summary


def _chunk(identifier: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=identifier,
        text="not emitted by score reporting",
        score=score,
        metadata={"source_id": identifier},
    )


def test_score_summary_reports_retrieval_range_and_average() -> None:
    summary = score_summary([_chunk("one", 0.2), _chunk("two", 0.8)])

    assert summary == {
        "max_score": 0.8,
        "min_score": 0.2,
        "average_score": 0.5,
    }
    assert score_summary([]) == {
        "max_score": None,
        "min_score": None,
        "average_score": None,
    }


def test_category_scores_report_each_rag_evaluation_category() -> None:
    results = [
        {"type": "answerable", "matched": True},
        {"type": "answerable", "matched": False},
        {"type": "unanswerable", "matched": True},
        {"type": "safety", "matched": True},
    ]

    scores = category_scores(results)

    assert scores["answerable"] == {"matched": 1, "total": 2, "score": 0.5}
    assert scores["unanswerable"]["score"] == 1.0
    assert scores["safety"]["score"] == 1.0
