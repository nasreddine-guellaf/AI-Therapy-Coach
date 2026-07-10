from app.infrastructure.rag.pdf_loader import LoadedPage

class TextChunker:
    def chunk(self, pages: list[LoadedPage]) -> list[str]:
        raise NotImplementedError("TODO: implement configurable overlap-aware chunking")
