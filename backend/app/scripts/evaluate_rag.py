"""Run deterministic retrieval and safety checks without calling an LLM."""

import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path

from app.core.config import settings
from app.domain.interfaces.retriever import RetrievedChunk
from app.domain.services.rag_context_policy import RAGContextPolicy
from app.domain.services.safety_service import SafetyService
from app.infrastructure.rag.embeddings import LocalE5EmbeddingProvider
from app.infrastructure.rag.retriever import Retriever
from app.infrastructure.vector_db.qdrant_client import QdrantVectorStore


DEFAULT_DATASET = (
    Path(__file__).resolve().parents[2] / "evaluations" / "rag" / "dataset.json"
)


def load_dataset(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != 30:
        raise ValueError("RAG evaluation dataset must contain exactly 30 items")
    return items


def score_summary(chunks: list[RetrievedChunk]) -> dict[str, float | None]:
    """Return safe retrieval aggregates without document or query text."""
    scores = [chunk.score for chunk in chunks]
    if not scores:
        return {"max_score": None, "min_score": None, "average_score": None}
    return {
        "max_score": max(scores),
        "min_score": min(scores),
        "average_score": sum(scores) / len(scores),
    }


def category_scores(results: list[dict]) -> dict[str, dict[str, float | int]]:
    """Aggregate pass rates for each evaluation category."""
    grouped: dict[str, list[bool]] = defaultdict(list)
    for result in results:
        grouped[result["type"]].append(bool(result["matched"]))
    return {
        category: {
            "matched": sum(matches),
            "total": len(matches),
            "score": sum(matches) / len(matches),
        }
        for category, matches in sorted(grouped.items())
    }


async def evaluate(dataset_path: Path) -> dict:
    retriever = Retriever(
        LocalE5EmbeddingProvider(settings.embedding_model),
        QdrantVectorStore(),
        min_score=settings.rag_min_score,
    )
    context_policy = RAGContextPolicy(
        settings.rag_document_question_min_score
    )
    safety_service = SafetyService()
    results: list[dict] = []

    for index, item in enumerate(load_dataset(dataset_path), start=1):
        item_type = item["type"]
        expected_source_ids = set(item.get("expected_source_ids", []))
        if item_type == "safety":
            assessment = safety_service.assess(item["question"])
            matched = (
                assessment.requires_immediate_escalation
                or assessment.professional_help_recommended
            )
            results.append(
                {
                    "id": index,
                    "type": item_type,
                    "matched": matched,
                    "retrieved_chunk_count": 0,
                    "accepted_chunk_count": 0,
                    "source_ids": [],
                    "retrieved_chunks": [],
                    "max_score": None,
                    "min_score": None,
                    "average_score": None,
                }
            )
            continue

        retrieved_chunks = await retriever.retrieve_relevant_chunks(
            item["question"],
            top_k=settings.rag_top_k,
        )
        decision = context_policy.select(
            item["question"],
            retrieved_chunks,
            document_specific=True if item_type == "unanswerable" else None,
        )
        accepted_chunks = decision.chunks
        source_ids = {chunk.source_id for chunk in accepted_chunks}
        if item_type == "unanswerable":
            # The generation layer may still provide safe general guidance.
            # Retrieval succeeds when it supplies no document attribution.
            matched = not accepted_chunks
        elif expected_source_ids:
            matched = expected_source_ids.issubset(source_ids)
        else:
            matched = bool(accepted_chunks)

        accepted_ids = {chunk.id for chunk in accepted_chunks}
        result = {
            "id": index,
            "type": item_type,
            "matched": matched,
            "document_specific": decision.document_specific,
            "retrieved_chunk_count": len(retrieved_chunks),
            "accepted_chunk_count": len(accepted_chunks),
            "source_ids": sorted(source_ids),
            "retrieved_chunks": [
                {
                    "source_id": chunk.source_id,
                    "score": chunk.score,
                    "accepted_for_grounding": chunk.id in accepted_ids,
                }
                for chunk in retrieved_chunks
            ],
            **score_summary(retrieved_chunks),
        }
        if item_type == "unanswerable":
            result["expected_response_mode"] = (
                "safe_general_fallback_without_sources"
            )
        results.append(result)

    matched_count = sum(bool(item["matched"]) for item in results)
    return {
        "dataset": str(dataset_path),
        "total": len(results),
        "matched": matched_count,
        "match_rate": matched_count / len(results),
        "category_scores": category_scores(results),
        "rag_min_score": settings.rag_min_score,
        "rag_document_question_min_score": (
            settings.rag_document_question_min_score
        ),
        "rag_top_k": settings.rag_top_k,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed-knowledge retrieval without invoking an LLM.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    arguments = parser.parse_args(argv)

    report = asyncio.run(evaluate(arguments.dataset.resolve()))
    serialized = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    if arguments.fail_on_mismatch and report["matched"] != report["total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
