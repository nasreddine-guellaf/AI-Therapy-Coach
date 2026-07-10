from abc import ABC, abstractmethod

class SpeechToText(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes) -> str: ...
