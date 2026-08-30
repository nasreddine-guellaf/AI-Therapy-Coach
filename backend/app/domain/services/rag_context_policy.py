"""Deterministic policy for deciding when retrieved evidence is usable."""

from dataclasses import dataclass
from unicodedata import combining, normalize

from app.domain.interfaces.retriever import RetrievedChunk


@dataclass(frozen=True, slots=True)
class RAGContextDecision:
    """Describe the evidence allowed into a hybrid RAG answer."""

    chunks: list[RetrievedChunk]
    document_specific: bool
    insufficient_document_context: bool


class RAGContextPolicy:
    """Select grounded evidence while allowing an honest general fallback."""

    _DOCUMENT_MARKERS = (
        "according to the document",
        "according to the documents",
        "according to the guide",
        "according to the guides",
        "according to the knowledge base",
        "based on the document",
        "based on these documents",
        "in the document",
        "in the documents",
        "what does the guide say",
        "what do the guides say",
        "the guide recommend",
        "the guides recommend",
        "recommended by the guide",
        "recommended by the guides",
        "knowledge base suggest",
        "does the knowledge base",
        "in the knowledge base",
        "described in the knowledge base",
        "documents' recommendations",
        "across the documents",
        "guides together",
        "documented approach",
        "knowledge base guidance",
        "included in the documents",
        "selon le document",
        "selon les documents",
        "selon le guide",
        "selon les guides",
        "d'apres le document",
        "d'apres les documents",
        "dans le document",
        "dans les documents",
        "que dit le guide",
        "que disent les guides",
        "base de connaissances",
        "dans la base de connaissances",
        "les guides proposent",
        "conseils des documents",
        "mentionnees dans la base",
        "mentionne dans",
        "mentionnes dans",
    )
    _FRENCH_MARKERS = (
        "selon ",
        "d'apres ",
        "dans les documents",
        "que dit ",
        "que disent ",
        "les documents",
        "le guide",
        "les guides",
    )

    def __init__(self, document_question_min_score: float = 0.35) -> None:
        if not -1.0 <= document_question_min_score <= 1.0:
            raise ValueError(
                "document_question_min_score must be between -1 and 1"
            )
        self.document_question_min_score = document_question_min_score

    def select(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        document_specific: bool | None = None,
    ) -> RAGContextDecision:
        """Return evidence strong enough for the question's document scope."""
        is_document_specific = (
            self.is_document_specific(question)
            if document_specific is None
            else document_specific
        )
        selected = (
            [
                chunk
                for chunk in chunks
                if chunk.score >= self.document_question_min_score
            ]
            if is_document_specific
            else list(chunks)
        )
        return RAGContextDecision(
            chunks=selected,
            document_specific=is_document_specific,
            insufficient_document_context=(
                is_document_specific and not selected
            ),
        )

    @classmethod
    def is_document_specific(cls, question: str) -> bool:
        normalized = cls._normalize(question)
        return any(marker in normalized for marker in cls._DOCUMENT_MARKERS)

    @classmethod
    def insufficiency_notice(cls, question: str) -> str:
        """Return a localized disclosure to prefix before general guidance."""
        normalized = cls._normalize(question)
        if any(marker in normalized for marker in cls._FRENCH_MARKERS):
            return (
                "Les documents disponibles ne donnent pas assez "
                "d\u2019informations sur ce point."
            )
        return (
            "The available documents do not provide enough information on "
            "this point."
        )

    @classmethod
    def add_insufficiency_notice(cls, question: str, response: str) -> str:
        """Ensure fallback advice is not presented as document evidence."""
        notice = cls.insufficiency_notice(question)
        if cls._normalize(notice) in cls._normalize(response):
            return response.strip()
        return f"{notice}\n\n{response.strip()}"

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = normalize("NFKD", value.casefold().replace("\u2019", "'"))
        without_accents = "".join(
            character for character in decomposed if not combining(character)
        )
        return " ".join(without_accents.split())
