from app.domain.interfaces.speech_to_text import SpeechToText

class WhisperSpeechToText(SpeechToText):
    async def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError("TODO: configure Whisper")
