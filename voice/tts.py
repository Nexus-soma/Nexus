"""
Nexus Text-to-Speech
Uses Piper for natural voice or espeak-ng as fallback.
"""

import subprocess
import os
import tempfile

class TextToSpeech:
    def __init__(self, model_path=None):
        # Try Piper first
        piper_binary = os.path.expanduser("~/piper/piper/piper")
        if os.path.exists(piper_binary):
            self.engine = "piper"
            self.binary = piper_binary
            self.model = model_path or os.path.expanduser("~/piper/en_US-lessac-medium.onnx")
        else:
            # Fallback to espeak
            self.engine = "espeak"
            self.binary = "espeak-ng"

    def speak(self, text: str):
        """Convert text to speech and play it."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name

        if self.engine == "piper":
            result = subprocess.run(
                ["bash", "-c", f"echo '{text}' | {self.binary} --model {self.model} --output_file {audio_path}"],
                capture_output=True
            )
        else:
            subprocess.run(
                [self.binary, text, "-w", audio_path],
                capture_output=True
            )

        # Play the audio
        subprocess.run(["paplay", audio_path])
        os.remove(audio_path)

    def speak_response(self, text: str, blocking: bool = False):
        """Speak a response. If blocking=False, plays in background."""
        if blocking:
            self.speak(text)
        else:
            import threading
            t = threading.Thread(target=self.speak, args=(text,))
            t.daemon = True
            t.start()
