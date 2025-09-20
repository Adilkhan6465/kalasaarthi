# speech_to_text_main.py

from modules.speech_to_text_gcp import transcribe_audio_bytes as gcp_transcribe
from gemini_fallback import transcribe_with_gemini

def transcribe_audio(wav_bytes, language_code="hi-IN"):
    try:
        result = gcp_transcribe(wav_bytes, language_code)
        return result
    except Exception as e:
        print("GCP transcription failed:", e)
        result = transcribe_with_gemini(wav_bytes, language_code)
        return result