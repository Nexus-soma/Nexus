"""
Nexus Speech-to-Text
Uses Whisper.cpp for local, offline transcription.
"""

import subprocess
import os
import tempfile

class SpeechToText:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")
        self.model_path = model_path
        self.binary = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")

    def transcribe(self, audio_path: str) -> str:
        """Convert audio file to text."""
        if not os.path.exists(audio_path):
            return ""

        result = subprocess.run(
            [self.binary, "-m", self.model_path, "-f", audio_path, "--no-timestamps", "-oj"],
            capture_output=True, text=True
        )

        # Whisper outputs JSON with the transcription
        output = result.stdout.strip()
        if output:
            import json
            try:
                data = json.loads(output)
                return data.get("text", "").strip()
            except json.JSONDecodeError:
                return output.strip()
        return ""

    def transcribe_from_mic(self, duration: int = 5) -> str:
        """Record from microphone and transcribe."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name

        # Record audio using arecord (ALSA) or parec (PulseAudio)
        subprocess.run(
            ["parec", "--format=s16le", "--rate=16000", "--channels=1",
             "--file-format=wav", audio_path],
            timeout=duration
        )

        text = self.transcribe(audio_path)
        os.remove(audio_path)
        return text
