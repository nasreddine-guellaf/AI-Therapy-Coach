"""Tests for hybrid document-grounding decisions."""

from app.domain.interfaces.retriever import RetrievedChunk
from app.domain.services.rag_context_policy import RAGContextPolicy


def _chunk(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id="point",
        text="Potential context",
        score=score,
        metadata={"source_id": "source"},
    )


def test_weak_document_context_is_removed_for_hybrid_fallback() -> None:
    decision = RAGContextPolicy(0.35).select(
        "According to the documents, what should I do?",
        [_chunk(0.34)],
    )

    assert decision.document_specific
    assert decision.insufficient_document_context
    assert decision.chunks == []


def test_general_coaching_keeps_chunks_that_pass_base_retrieval() -> None:
    decision = RAGContextPolicy(0.35).select(
        "Can you help me reflect on this feeling?",
        [_chunk(0.30)],
    )

    assert not decision.document_specific
    assert not decision.insufficient_document_context
    assert len(decision.chunks) == 1


def test_french_document_fallback_notice_is_stable() -> None:
    response = RAGContextPolicy.add_insufficiency_notice(
        "Selon les documents, que puis-je faire ?",
        "Tu peux commencer par une petite étape.",
    )

    assert response.startswith(
        "Les documents disponibles ne donnent pas assez "
        "d\u2019informations sur ce point."
    )
    assert "petite étape" in response
