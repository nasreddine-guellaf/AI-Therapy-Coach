from app.domain.interfaces.text_to_speech import TextToSpeech

class ElevenLabsTextToSpeech(TextToSpeech):
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError("TODO: configure ElevenLabs")
