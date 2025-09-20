from google.cloud import speech_v1p1beta1 as speech
from pydub import AudioSegment
import io

def convert_to_wav_bytes(file_bytes: bytes, file_ext: str = "mp3", target_rate: int = 16000):
    audio = AudioSegment.from_file(io.BytesIO(file_bytes), format=file_ext)
    audio = audio.set_frame_rate(target_rate).set_channels(1).set_sample_width(2)
    out = io.BytesIO()
    audio.export(out, format="wav")
    return out.getvalue()

def transcribe_audio_bytes(wav_bytes: bytes, language_code: str = "hi-IN"):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=wav_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )
    response = client.recognize(config=config, audio=audio)
    transcripts = []
    for result in response.results:
        transcripts.append(result.alternatives[0].transcript)
    return " ".join(transcripts)