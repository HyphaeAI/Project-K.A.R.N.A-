"""
GCS Video Vault — Write-Only
============================
This module provides write-only access to the GCS video vault.
NO read or download operations are exposed here, by design.
Video is stored solely for audit/compliance purposes and is never
passed to any AI model or read back by the application.
"""

import logging
import os
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton client
# ---------------------------------------------------------------------------

_client: Optional[storage.Client] = None


def init_gcs_client() -> storage.Client:
    """
    Initialize and return a GCS client.

    If GOOGLE_APPLICATION_CREDENTIALS is set in the environment, credentials
    are loaded from that service account key file. Otherwise, Application
    Default Credentials (ADC) are used (e.g., Workload Identity on Cloud Run).
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        logger.debug("Initializing GCS client from service account file: %s", creds_path)
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        return storage.Client(credentials=credentials)

    logger.debug("Initializing GCS client using Application Default Credentials")
    return storage.Client()


def _get_client() -> storage.Client:
    """Return the module-level singleton GCS client, initializing on first call."""
    global _client
    if _client is None:
        _client = init_gcs_client()
    return _client


# ---------------------------------------------------------------------------
# Write-only vault operations
# ---------------------------------------------------------------------------
# NOTE: No read or download methods are defined in this module.
# This is an intentional architectural constraint — the vault is write-only.
# ---------------------------------------------------------------------------


def vault_video_chunk(session_id: str, chunk_index: int, webm_bytes: bytes) -> str:
    """
    Upload a WebM video chunk to the GCS vault.

    Blob path: {session_id}/chunk_{chunk_index:03d}.webm
    Content type: video/webm

    Args:
        session_id:   The active interview session UUID.
        chunk_index:  Zero-based sequential chunk number.
        webm_bytes:   Raw WebM bytes to upload.

    Returns:
        The full GCS URI, e.g. ``gs://karna-vault/abc123/chunk_000.webm``.

    Raises:
        Exception: Re-raises any GCS upload error after logging it.
    """
    bucket_name = os.environ.get("GCS_BUCKET", "karna-vault")
    blob_path = f"{session_id}/chunk_{chunk_index:03d}.webm"

    try:
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(webm_bytes, content_type="video/webm")

        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        logger.info("Vaulted video chunk to %s (%d bytes)", gcs_uri, len(webm_bytes))
        return gcs_uri

    except Exception:
        logger.error(
            "Failed to vault video chunk for session=%s chunk=%d",
            session_id,
            chunk_index,
            exc_info=True,
        )
        raise
