import json
import unittest

from agent.voice import ElevenLabsError, ElevenLabsVoiceClient


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json"):
        self.body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class VoiceTests(unittest.TestCase):
    def test_transcribe_posts_scribe_v1_and_returns_text(self):
        requests = []

        def transport(request, timeout):
            requests.append(request)
            return FakeResponse(json.dumps({"text": "Olá Jarvis"}).encode())

        client = ElevenLabsVoiceClient("secret-sentinel", "voice-1", transport=transport)

        self.assertEqual(client.transcribe(b"audio", "audio/webm"), "Olá Jarvis")
        self.assertIn(b"scribe_v1", requests[0].data)
        self.assertEqual(requests[0].headers["Xi-api-key"], "secret-sentinel")

    def test_speak_uses_multilingual_model_and_errors_redact_key(self):
        requests = []

        def transport(request, timeout):
            requests.append(request)
            return FakeResponse(b"mp3", "audio/mpeg")

        client = ElevenLabsVoiceClient("secret-sentinel", "voice-1", transport=transport)

        audio, content_type = client.speak("Bom dia")

        self.assertEqual((audio, content_type), (b"mp3", "audio/mpeg"))
        self.assertEqual(json.loads(requests[0].data)["model_id"], "eleven_multilingual_v2")
        self.assertIn("output_format=mp3_44100_128", requests[0].full_url)
        self.assertNotIn("secret-sentinel", repr(client))

    def test_voice_id_is_url_quoted_and_untrusted_provider_data_is_not_exposed(self):
        def transport(request, timeout):
            raise RuntimeError("secret-sentinel provider body")

        client = ElevenLabsVoiceClient("secret-sentinel", "voice id/../../?x=1", transport=transport)

        with self.assertRaises(ElevenLabsError) as raised:
            client.speak("Bom dia")

        self.assertEqual(raised.exception.code, "ELEVENLABS_REQUEST_FAILED")
        self.assertNotIn("secret-sentinel", str(raised.exception))
        self.assertNotIn("provider body", str(raised.exception))
        self.assertNotIn("secret-sentinel", repr(raised.exception))

    def test_invalid_audio_text_or_provider_response_is_rejected(self):
        client = ElevenLabsVoiceClient("secret-sentinel", "voice-1", transport=lambda *_: FakeResponse(b"{}"))

        for audio, mime_type in ((b"", "audio/webm"), (b"audio", "text/plain")):
            with self.assertRaises(ElevenLabsError):
                client.transcribe(audio, mime_type)
        for text in ("", "  ", "x" * 2001):
            with self.assertRaises(ElevenLabsError):
                client.speak(text)
        with self.assertRaises(ElevenLabsError) as raised:
            client.transcribe(b"audio", "audio/webm")
        self.assertEqual(raised.exception.code, "ELEVENLABS_INVALID_RESPONSE")

    def test_transcription_rejects_malformed_or_empty_provider_payloads(self):
        responses = iter((FakeResponse(b"not-json"), FakeResponse(b'{"text": "  "}')))
        client = ElevenLabsVoiceClient("secret-sentinel", "voice-1", transport=lambda *_: next(responses))

        for expected_code in ("ELEVENLABS_INVALID_RESPONSE", "TRANSCRIPTION_EMPTY"):
            with self.assertRaises(ElevenLabsError) as raised:
                client.transcribe(b"audio", "audio/webm")
            self.assertEqual(raised.exception.code, expected_code)
