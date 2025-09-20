# gemini_fallback.py

def transcribe_with_gemini(wav_bytes, language_code="hi-IN"):
    if language_code == "hi-IN":
        return "क्रेडिट उपलब्ध नहीं हैं। कृपया बाद में प्रयास करें।"
    elif language_code == "en-US":
        return "Credits not available. Please try later."
    else:
        return "Credits not available."