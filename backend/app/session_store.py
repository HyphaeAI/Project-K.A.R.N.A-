from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data structures (design §4.2 and §4.1)
# ---------------------------------------------------------------------------


@dataclass
class RoundRecord:
    """Represents a single question-answer cycle (design §4.2)."""

    round: int
    topic_area: str
    question: str
    question_type: str          # "initial" | "follow_up_probe" | "clarification"
    transcript: str
    scores: dict
    flags: dict
    evaluator_notes: str
    follow_ups: list = field(default_factory=list)  # List[RoundRecord]


@dataclass
class SessionState:
    """In-memory session object (design §4.1)."""

    session_id: str
    job_role: str
    status: str = "active"      # "active" | "completed"
    total_rounds: int = 5
    current_round: int = 1
    current_chunk_buffer: list = field(default_factory=list)   # audio WAV paths
    transcript_history: list = field(default_factory=list)     # List[RoundRecord]
    cumulative_scores: dict = field(default_factory=dict)
    flags: dict = field(
        default_factory=lambda: {"memorization_count": 0, "follow_up_count": 0}
    )
    created_at: datetime = field(default_factory=datetime.utcnow)
    gemini_chat_history: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_sessions: dict[str, SessionState] = {}


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def create_session(job_role: str) -> SessionState:
    """Create a new session, persist it in the store, and return it."""
    session_id = str(uuid.uuid4())
    total_rounds = int(os.environ.get("TOTAL_ROUNDS", 5))
    session = SessionState(
        session_id=session_id,
        job_role=job_role,
        total_rounds=total_rounds,
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    """Return the session for *session_id*, or None if not found."""
    return _sessions.get(session_id)


def update_session(session_id: str, **kwargs: Any) -> Optional[SessionState]:
    """Update arbitrary fields on a session and return the updated object.

    Returns None if the session does not exist.
    """
    session = _sessions.get(session_id)
    if session is None:
        return None
    for key, value in kwargs.items():
        setattr(session, key, value)
    return session
