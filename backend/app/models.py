from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_ROLES: list[str] = [
    "Backend Engineer",
    "Frontend Engineer",
    "ML Engineer",
    "DevOps Engineer",
    "Full Stack Engineer",
]

# ---------------------------------------------------------------------------
# Shared / nested models
# ---------------------------------------------------------------------------


class QuestionPayload(BaseModel):
    text: str
    type: str
    topic_area: str


class OperationLog(BaseModel):
    op: str
    gcs_path: str | None = None
    duration_ms: int | None = None
    word_count: int | None = None
    latency_ms: int | None = None
    reason: str | None = None


class EvaluationScores(BaseModel):
    system_design: int
    problem_solving: int
    communication_clarity: int
    depth_of_knowledge: int
    adaptability: int

    model_config = {
        "populate_by_name": True,
    }

    # Allow the JSON keys used by Gemini (e.g. "System Design") to map to
    # the snake_case field names via aliases.
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        if isinstance(obj, dict):
            alias_map = {
                "System Design": "system_design",
                "Problem Solving": "problem_solving",
                "Communication Clarity": "communication_clarity",
                "Depth of Knowledge": "depth_of_knowledge",
                "Adaptability": "adaptability",
            }
            obj = {alias_map.get(k, k): v for k, v in obj.items()}
        return super().model_validate(obj, *args, **kwargs)


class EvaluationFlags(BaseModel):
    memorization_detected: bool
    answer_quality: str


class EvaluationResult(BaseModel):
    scores: EvaluationScores
    flags: EvaluationFlags
    evaluator_notes: str


class NextAction(BaseModel):
    type: str
    current_round: int
    question: Optional[QuestionPayload] = None
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# /init  request / response
# ---------------------------------------------------------------------------


class InitRequest(BaseModel):
    job_role: str

    @field_validator("job_role")
    @classmethod
    def validate_job_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(
                f"Invalid job_role. Must be one of: {', '.join(ALLOWED_ROLES)}"
            )
        return v


class InitResponse(BaseModel):
    session_id: str
    current_round: int
    total_rounds: int
    question: QuestionPayload
    status: str


# ---------------------------------------------------------------------------
# /process-chunk  response
# ---------------------------------------------------------------------------


class ChunkResponse(BaseModel):
    session_id: str
    chunk_index: int
    status: str
    transcript: Optional[str] = None
    evaluation: Optional[EvaluationResult] = None
    next_action: Optional[NextAction] = None
    operations: list[OperationLog]


# ---------------------------------------------------------------------------
# /results  response
# ---------------------------------------------------------------------------


class RoundDetail(BaseModel):
    round: Optional[int] = None
    topic_area: Optional[str] = None
    question: str
    question_type: str
    transcript: str
    scores: EvaluationScores
    flags: EvaluationFlags
    evaluator_notes: str
    follow_ups: list[RoundDetail] = []


# Self-referential model requires a rebuild after the class is fully defined.
RoundDetail.model_rebuild()


class VideoVaultManifest(BaseModel):
    bucket: str
    prefix: str
    total_chunks: int
    note: str


class ResultsResponse(BaseModel):
    session_id: str
    job_role: str
    status: str
    overall_score: int
    recommendation: str
    skill_scores: EvaluationScores
    flags: EvaluationFlags
    round_details: list[RoundDetail]
    summary: str
    video_vault_manifest: VideoVaultManifest
