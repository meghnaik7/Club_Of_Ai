import asyncio
import base64
import sys
from app.voice.sarvam_client import SarvamClient
from app.voice.tts_service import TTSService
from app.voice.stt_service import STTService
from app.voice.schemas import TranscriptionResponse

async def main():
    print("==================================================")
    print("LIVE MULTILINGUAL VERIFICATION (SARVAM AI)")
    print("==================================================")

    client = SarvamClient()
    tts = TTSService(client=client)

    test_cases = [
        ("en-IN", "Create a task for Rahul to prepare the venue tomorrow."),
        ("hi-IN", "राहुल के लिए वेन्यू तैयार करने का एक टास्क बनाओ।"),
        ("gu-IN", "રાહુલ માટે વેન્યુ તૈયાર કરવાનો એક ટાસ્ક બનાવો."),
    ]

    for lang, sample_text in test_cases:
        print(f"\n--- Testing Language: {lang} ---")
        print(f"Original Text: {sample_text}")

        # 1. TTS Synthesis
        tts_res = await tts.synthesize_speech(text=sample_text, language=lang)
        print(f"TTS Success: Received {len(tts_res.audio_base64)} base64 chars for voice '{tts_res.voice}'")
        raw_audio = base64.b64decode(tts_res.audio_base64)
        print(f"Raw Audio Size: {len(raw_audio)} bytes (MIME: {tts_res.content_type})")

        # 2. STT Transcription
        stt_res = await client.speech_to_text(
            audio_bytes=raw_audio,
            filename=f"test_{lang}.wav",
            content_type="audio/wav",
            language_code=lang
        )
        print(f"STT Transcript: {stt_res['transcript']}")
        print(f"STT Language Code: {stt_res['language_code']}")
        print(f"STT Confidence/Prob: {stt_res['confidence']}")

    print("\n==================================================")
    print("ALL LIVE TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
