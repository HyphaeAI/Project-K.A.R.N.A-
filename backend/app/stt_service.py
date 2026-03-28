"""Google Cloud Speech-to-Text integration for Project K.A.R.N.A."""

import logging
import os

from google.api_core import exceptions as gcp_exceptions
from google.cloud import speech
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_client: speech.SpeechClient | None = None


def init_stt_client() -> speech.SpeechClient:
    """Initialize and return a Google Cloud SpeechClient.

    Uses GOOGLE_APPLICATION_CREDENTIALS env var if set (service account file),
    otherwise falls back to Application Default Credentials.
    """
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        logger.info("Initializing STT client with service account credentials from %s", credentials_path)
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return speech.SpeechClient(credentials=credentials)

    logger.info("Initializing STT client with Application Default Credentials")
    return speech.SpeechClient()


def _get_client() -> speech.SpeechClient:
    """Return the module-level singleton STT client, initializing on first call."""
    global _client
    if _client is None:
        _client = init_stt_client()
    return _client


def transcribe_audio(wav_path: str, timeout: float = 30.0) -> str:
    """Transcribe a WAV audio file using Google Cloud Speech-to-Text.

    Args:
        wav_path: Path to a 16kHz mono 16-bit PCM WAV file.
        timeout: Maximum seconds to wait for the STT API response.

    Returns:
        The transcribed text, or "" if no speech was detected.

    Raises:
        TimeoutError: If the STT API call exceeds the timeout.
        Exception: Re-raises any other unexpected error from the API.
    """
    client = _get_client()

    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    audio = speech.RecognitionAudio(content=wav_bytes)

    try:
        response = client.recognize(config=config, audio=audio, timeout=timeout)
    except gcp_exceptions.DeadlineExceeded as exc:
        logger.error("STT request timed out after %.1fs for file %s", timeout, wav_path)
        raise TimeoutError(f"Speech-to-Text timed out after {timeout}s") from exc
    except Exception:
        logger.exception("Unexpected error during STT transcription of %s", wav_path)
        raise

    if not response.results:
        logger.warning("STT returned no results for file %s", wav_path)
        return ""

    transcript = response.results[0].alternatives[0].transcript
    logger.info("Transcribed %d character(s) from %s", len(transcript), wav_path)
    return transcript
