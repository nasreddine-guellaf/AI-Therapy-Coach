from abc import ABC, abstractmethod

class TextToSpeech(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes: ...
