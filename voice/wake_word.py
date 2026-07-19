"""
Nexus Wake Word Detector
Listens for "Hey Nexus" or "Nexus" activation phrase.
Uses Whisper.cpp for streaming transcription.
"""

import subprocess
import os
import tempfile
import time

class WakeWordDetector:
    def __init__(self, stt, wake_words=None):
        self.stt = stt
        self.wake_words = wake_words or ["kip", "hey kip", "okay"]
        self.is_listening = False

    def listen_for_wake_word(self, timeout: int = 10) -> bool:
        self.is_listening = True
        start_time = time.time()

        while self.is_listening and (time.time() - start_time) < timeout:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                audio_path = f.name

            proc = subprocess.Popen(
                ["parec", "--format=s16le", "--rate=16000", "--channels=1",
                 "--file-format=wav", audio_path]
            )
            time.sleep(3)
            proc.terminate()
            proc.wait()

            text = self.stt.transcribe(audio_path).lower()
            os.remove(audio_path)

            for word in self.wake_words:
                if word in text:
                    self.is_listening = False
                    return True

            time.sleep(0.5)

        self.is_listening = False
        return False

    def stop(self):
        self.is_listening = False
