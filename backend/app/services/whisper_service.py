import os
import tempfile
import wave
import io
from groq import Groq

# ===============================
# 🔐 CONFIG
# ===============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Groq's Whisper endpoint — fast and free tier is generous
WHISPER_MODEL = "whisper-large-v3-turbo"


# ===============================
# 🎤 TRANSCRIBE AUDIO BYTES
# ===============================
def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """
    Accepts raw audio bytes from the browser (WebM/Opus from MediaRecorder).
    Sends to Groq Whisper for transcription.
    Returns the transcribed text string.
    """

    if not audio_bytes or len(audio_bytes) < 1000:
        print("[WHISPER] Audio too short, skipping")
        return ""

    try:
        # Groq expects a file-like object with a name
        # We use a named tuple trick to give it a filename with the right extension
        audio_file = ("audio.webm", io.BytesIO(audio_bytes), mime_type)

        response = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            language="en",
            response_format="text"
        )

        # Groq returns plain string when response_format="text"
        transcript = response.strip() if isinstance(response, str) else response.text.strip()

        print(f"[WHISPER] Transcribed: {transcript[:100]}...")
        return transcript

    except Exception as e:
        print(f"[WHISPER ERROR] {e}")
        return ""