"""Data models for mtvgen."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class LyricWord:
    """A single word with precise timing."""

    word: str
    start: float  # seconds
    end: float  # seconds

    def to_dict(self) -> dict:
        return {"word": self.word, "start": round(self.start, 3), "end": round(self.end, 3)}


@dataclass
class LyricLine:
    """A single lyric line with timing and optional word-level breakdown."""

    text: str
    start: float  # seconds
    end: float  # seconds
    words: Optional[list[LyricWord]] = None

    def to_dict(self) -> dict:
        d = {
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
        }
        if self.words:
            d["words"] = [w.to_dict() for w in self.words]
        else:
            d["words"] = None
        return d


@dataclass
class SongData:
    """Complete song data including metadata and lyrics."""

    title: str
    artist: str
    duration: float  # seconds
    lyrics: list[LyricLine] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "duration": round(self.duration, 3),
            "lyrics": [line.to_dict() for line in self.lyrics],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
