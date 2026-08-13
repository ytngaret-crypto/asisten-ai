import asyncio
import base64
import io
import wave

from google import genai
from google.genai import types
from app.config import Settings


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_text(self, prompt, system_instruction="", use_search=False):
        def call():
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or None,
                temperature=0.7,
            )
            if use_search:
                # Google Search grounding for the generateContent API.
                config.tools = [types.Tool(google_search=types.GoogleSearch())]

            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=config,
            )
            return response.text or ""

        return (await asyncio.to_thread(call)).strip()

    async def vision(self, data: bytes, mime_type: str, prompt: str):
        def call():
            part = types.Part.from_bytes(data=data, mime_type=mime_type)
            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[part, prompt],
                config=types.GenerateContentConfig(temperature=0.3),
            )
            return response.text or ""

        return (await asyncio.to_thread(call)).strip()

    async def generate_image(self, prompt: str):
        def call():
            interaction = self.client.interactions.create(
                model=self.settings.gemini_image_model,
                input=prompt,
            )
            output = getattr(interaction, "output_image", None)
            if not output:
                return None
            return base64.b64decode(output.data)

        return await asyncio.to_thread(call)

    @staticmethod
    def _pcm_to_wav(pcm: bytes, sample_rate=24000, channels=1, sample_width=2):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buffer.getvalue()

    async def tts(self, text: str, voice: str):
        # Gemini 3.1 Flash TTS is more reliable when the prompt explicitly
        # tells the model to synthesize speech and clearly marks the text to speak.
        # This also avoids vague-prompt classifier rejections (PROHIBITED_CONTENT).
        spoken_text = text.strip()
        if not spoken_text:
            raise ValueError("Teks TTS kosong.")

        prompt = (
            "Synthesize the following text as natural speech. "
            "Do not explain, translate, summarize, or add any words. "
            "Only speak the exact text between <speak> and </speak>.\n\n"
            f"<speak>{spoken_text}</speak>"
        )

        def call():
            interaction = self.client.interactions.create(
                model=self.settings.gemini_tts_model,
                input=prompt,
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"voice": voice}
                    ]
                },
            )
            output = getattr(interaction, "output_audio", None)
            if not output or not getattr(output, "data", None):
                raise RuntimeError("Gemini TTS tidak mengembalikan audio.")
            pcm = base64.b64decode(output.data)
            return self._pcm_to_wav(pcm)

        return await asyncio.to_thread(call)
