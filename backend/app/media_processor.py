"""
Media Processing Pipeline — FFmpeg-based audio/video handling.
Design reference: spec/design.md §7.1 and §7.2
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def save_temp_chunk(session_id: str, chunk_index: int, chunk_bytes: bytes) -> str:
    """
    Save a WebM chunk to /tmp/{session_id}/chunk_{chunk_index}.webm.

    Creates the directory if it doesn't exist.
    Returns the file path.
    """
    dir_path = Path("/tmp") / session_id
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"chunk_{chunk_index}.webm"
    file_path.write_bytes(chunk_bytes)

    logger.info("Saved temp chunk: %s", file_path)
    return str(file_path)


def extract_audio(webm_path: str) -> str:
    """
    Extract audio from a WebM file using FFmpeg.

    Runs: ffmpeg -i {webm_path} -vn -acodec pcm_s16le -ar 16000 -ac 1 {wav_path}
    Output path: same directory as input, .wav extension replacing .webm.

    Raises RuntimeError on FFmpeg failure.
    Returns the WAV file path.
    """
    webm = Path(webm_path)
    wav_path = webm.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-y",           # overwrite output if exists
        "-i", str(webm),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(wav_path),
    ]

    logger.info("Extracting audio: %s -> %s", webm_path, wav_path)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("FFmpeg audio extraction failed for %s: %s", webm_path, result.stderr)
        raise RuntimeError(
            f"FFmpeg failed to extract audio from {webm_path}: {result.stderr}"
        )

    logger.info("Audio extracted successfully: %s", wav_path)
    return str(wav_path)


def concatenate_audio_chunks(wav_paths: list[str]) -> str:
    """
    Concatenate multiple WAV files into a single full_answer.wav.

    If only one path is provided, returns it directly (no concat needed).
    Derives the output directory from the first path's parent.

    Runs: ffmpeg -i "concat:path1|path2|..." -acodec pcm_s16le -ar 16000 -ac 1 {output_path}

    Raises RuntimeError on FFmpeg failure.
    Returns the output WAV path.
    """
    if not wav_paths:
        raise ValueError("wav_paths must not be empty")

    if len(wav_paths) == 1:
        logger.info("Single audio chunk — skipping concatenation: %s", wav_paths[0])
        return wav_paths[0]

    session_dir = Path(wav_paths[0]).parent
    output_path = session_dir / "full_answer.wav"

    concat_input = "concat:" + "|".join(wav_paths)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", concat_input,
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]

    logger.info("Concatenating %d audio chunks -> %s", len(wav_paths), output_path)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("FFmpeg concatenation failed: %s", result.stderr)
        raise RuntimeError(f"FFmpeg failed to concatenate audio chunks: {result.stderr}")

    logger.info("Audio concatenation complete: %s", output_path)
    return str(output_path)


def cleanup_temp_files(session_id: str) -> None:
    """
    Remove /tmp/{session_id}/ and all its contents.

    Logs a warning if the directory doesn't exist (does not raise).
    """
    dir_path = Path("/tmp") / session_id

    if not dir_path.exists():
        logger.warning("Temp directory does not exist, nothing to clean up: %s", dir_path)
        return

    shutil.rmtree(dir_path)
    logger.info("Cleaned up temp directory: %s", dir_path)
