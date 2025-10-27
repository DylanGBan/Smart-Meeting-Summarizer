import logging
import os
import tempfile
from math import ceil
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from moviepy import AudioFileClip
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(filename="debug.log", encoding="utf-8", level=logging.INFO)
    logger = logging.getLogger(__name__)

OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
client = OpenAI(api_key=OPEN_AI_KEY)

MAX_CHUNK_SECONDS = 1400


def _transcribe_file(file_obj) -> str:
    try:
        file_obj.seek(0, os.SEEK_END)
        size_bytes = file_obj.tell()
    except (AttributeError, OSError, ValueError):
        size_bytes = None
    finally:
        file_obj.seek(0)

    logger.info(
        "Sending transcription request%s",
        f" ({size_bytes} bytes)" if size_bytes is not None else "",
    )
    response = client.audio.transcriptions.create(
        model="gpt-4o-transcribe", file=file_obj, response_format="text"
    )
    logger.info("Transcription request completed successfully")
    file_obj.seek(0)
    return response


def _chunk_boundaries(duration_seconds: float, max_chunk_seconds: int) -> list[tuple[float, float]]:
    chunk_count = max(1, ceil(duration_seconds / max_chunk_seconds))
    chunk_duration = duration_seconds / chunk_count
    boundaries: list[tuple[float, float]] = []
    start = 0.0
    for index in range(chunk_count):
        end = start + chunk_duration
        if index == chunk_count - 1:
            end = duration_seconds
        boundaries.append((start, min(end, duration_seconds)))
        start = end
    return boundaries


def _split_audio(
    clip: AudioFileClip, chunk_seconds: int, basename: str, workdir: Path
) -> list[Path]:
    chunk_paths: list[Path] = []
    boundaries = _chunk_boundaries(clip.duration, chunk_seconds)

    subclip = None
    for index, (start, end) in enumerate(boundaries, start=1):
        chunk_path = workdir / f"{basename}_chunk_{index:03d}.mp3"
        try:
            subclip = clip.subclipped(start, end)
            subclip.write_audiofile(str(chunk_path))

            chunk_paths.append(chunk_path)
            logger.info(
                "Created chunk %s (%.2fs–%.2fs) in %s",
                chunk_path.name,
                start,
                end,
                workdir,
            )
        except Exception as exc:
            logger.warning("Transcription failed (possible with subclip=None): %s", exc)
            return None

    if subclip is not None:
        subclip.close()

    return chunk_paths


def file_extraction(file_path: str, *, chunk_seconds: int = MAX_CHUNK_SECONDS) -> str | None:
    if not isinstance(file_path, str):
        logger.warning("Invalid parameter input: expected path string")
        return None

    path = Path(file_path)
    if not path.is_file():
        logger.warning("File does not exist: %s", path)
        return None

    chunk_seconds = max(1, min(int(chunk_seconds), MAX_CHUNK_SECONDS))

    try:
        with AudioFileClip(str(path)) as audio_file:
            duration = audio_file.duration
            logger.info("Loaded audio '%s' (duration %.2f seconds)", path, duration)

            if duration <= chunk_seconds:
                logger.info("Audio fits within %s seconds; sending single request", chunk_seconds)
                with path.open("rb") as audio_data:
                    return _transcribe_file(audio_data)

            transcripts: list[str] = []
            basename = path.stem
            tmp_root = Path.cwd() / "tmp_chunks"
            tmp_root.mkdir(exist_ok=True)
            chunk_paths = _split_audio(audio_file, chunk_seconds, basename, tmp_root)
            logger.info("Prepared %d chunks for '%s' in %s", len(chunk_paths), path, tmp_root)

            try:
                for chunk in chunk_paths:
                    logger.info("Transcribing chunk %s", chunk.name)
                    with chunk.open("rb") as chunk_file:
                        transcripts.append(_transcribe_file(chunk_file))
            finally:
                for chunk in chunk_paths:
                    try:
                        chunk.unlink()
                        logger.info("Deleted temporary chunk %s", chunk.name)
                    except OSError:
                        logger.info("Failed to delete chunk %s (ignored)", chunk.name)

        return "".join(transcripts) if transcripts else None
    except Exception as exc:
        logger.warning("Transcription failed: %s", exc)
        return None
