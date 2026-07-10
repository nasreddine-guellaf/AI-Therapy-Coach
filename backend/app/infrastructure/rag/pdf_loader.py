from dataclasses import dataclass

@dataclass(frozen=True)
class LoadedPage:
    text: str
    page_number: int

class PDFLoader:
    def load(self, content: bytes) -> list[LoadedPage]:
        raise NotImplementedError("TODO: select and configure a PDF parser")
