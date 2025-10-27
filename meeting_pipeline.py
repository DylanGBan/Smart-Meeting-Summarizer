from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from speech_to_text import file_extraction
from summarization import meeting_bulletpoints, meeting_summary


@dataclass
class MeetingArtifacts:
    transcript: str
    bullet_points: Dict[str, list[str]]
    summary: str


def process_meeting(
    video_path: str,
    *,
    chunk_seconds: int = 600,
    summary_model: str = "gpt-4o-mini",
) -> Optional[MeetingArtifacts]:
    transcript = file_extraction(video_path, chunk_seconds=chunk_seconds)
    if not transcript:
        return None

    bullet_points = meeting_bulletpoints(transcript)
    summary = meeting_summary(transcript, model=summary_model)

    return MeetingArtifacts(
        transcript=transcript,
        bullet_points=bullet_points,
        summary=summary,
    )
