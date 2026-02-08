"""Cartesia TTS backend proxy — streams audio bytes to frontend."""

from __future__ import annotations

import os
from typing import Iterator, Optional

from cartesia import Cartesia


# Sonic 2 is Cartesia's latest model
MODEL_ID = "sonic-2"
# A clear, professional male voice — "Barbershop Man" is good for demos
VOICE_ID = "a0e99841-438c-4a64-b679-ae501e7d6091"


class CartesiaTTS:
    def __init__(self, api_key: Optional[str] = None):
        self.client = Cartesia(api_key=api_key or os.environ.get("CARTESIA_API_KEY", ""))

    def stream_audio(self, text: str) -> Iterator[bytes]:
        """Stream MP3 audio bytes for the given text."""
        return self.client.tts.bytes(
            model_id=MODEL_ID,
            transcript=text,
            voice={"mode": "id", "id": VOICE_ID},
            output_format={"container": "mp3", "bit_rate": 128000, "sample_rate": 44100},
            language="en",
        )
