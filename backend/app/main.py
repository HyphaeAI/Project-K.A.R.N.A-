import logging
import os
import time

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import gemini_service, gcs_service, media_processor, session_store, stt_service
from .models import (
    ChunkResponse,
    EvaluationFlags,
    EvaluationResult,
    EvaluationScores,
    InitRequest,
    InitResponse,
    NextAction,
    OperationLog,
    QuestionPayload,
    ResultsResponse,
    RoundDetail,
    VideoVaultManifest,
)
from .session_store import RoundRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="K.A.R.N.A. API")

# CORS
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.on_event("startup")
async def startup_handler():
    logger.info("K.A.R.N.A. backend starting up...")


@app.on_event("shutdown")
async def shutdown_handler():
    logger.info("K.A.R.N.A. backend shutting down...")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/init", response_model=InitResponse)
async def init_session(request: InitRequest):
    # Pydantic already raises 422 for missing fields; catch ValueError for invalid role
    try:
        # Validate by re-running the validator (already done by Pydantic, but
        # guard against any downstream ValueError too)
        job_role = request.job_role
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    # Create session
    session = session_store.create_session(job_role)

    # Generate first question (gemini_service is a placeholder for now)
    _FALLBACK_QUESTION = {
        "question_text": "Tell me about your experience with system design.",
        "topic_area": "System Design",
        "question_type": "initial",
        "difficulty": "medium",
    }

    try:
        question_dict = gemini_service.generate_initial_question(
            job_role,
            current_round=1,
            total_rounds=session.total_rounds,
            covered_topics=[],
            transcript_history=[],
        )
    except (NotImplementedError, AttributeError):
        question_dict = _FALLBACK_QUESTION

    # Store question in gemini_chat_history
    session.gemini_chat_history.append({"role": "model", "content": question_dict})
    session_store.update_session(session.session_id, gemini_chat_history=session.gemini_chat_history)

    question_payload = QuestionPayload(
        text=question_dict.get("question_text", ""),
        type=question_dict.get("question_type", "initial"),
        topic_area=question_dict.get("topic_area", ""),
    )

    return InitResponse(
        session_id=session.session_id,
        current_round=1,
        total_rounds=session.total_rounds,
        question=question_payload,
        status="active",
    )


# ---------------------------------------------------------------------------
# Fallback constants
# ---------------------------------------------------------------------------

_FALLBACK_EVAL: dict = {
    "scores": {
        "System Design": 70,
        "Problem Solving": 70,
        "Communication Clarity": 70,
        "Depth of Knowledge": 70,
        "Adaptability": 70,
    },
    "flags": {"memorization_detected": False, "answer_quality": "moderate"},
    "evaluator_notes": "Evaluation pending.",
    "probe_needed": False,
    "probe_question": None,
}


@app.post("/process-chunk", response_model=ChunkResponse)
async def process_chunk(
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    media_chunk: UploadFile = Form(...),
    is_final: str = Form(...),
):
    # Normalise is_final — HTML forms send strings
    is_final_bool: bool = is_final.strip().lower() == "true"

    # 1. Validate session
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Session not found or expired", "session_id": session_id},
        )

    # 2. Read chunk bytes
    chunk_bytes = await media_chunk.read()

    # 3. Save temp chunk
    webm_path = media_processor.save_temp_chunk(session_id, chunk_index, chunk_bytes)

    # 4. Extract audio
    wav_path = media_processor.extract_audio(webm_path)

    # 5. Vault video to GCS
    gcs_uri = gcs_service.vault_video_chunk(session_id, chunk_index, chunk_bytes)

    # 6. Append wav_path to chunk buffer
    session.current_chunk_buffer.append(wav_path)

    # 7. Build initial operations log
    operations: list[OperationLog] = [
        OperationLog(op="video_vaulted", gcs_path=gcs_uri),
        OperationLog(op="audio_extracted"),
    ]

    # ------------------------------------------------------------------
    # Non-final chunk — return early
    # ------------------------------------------------------------------
    if not is_final_bool:
        session_store.update_session(
            session_id,
            current_chunk_buffer=session.current_chunk_buffer,
        )
        return ChunkResponse(
            session_id=session_id,
            chunk_index=chunk_index,
            status="chunk_received",
            operations=operations,
        )

    # ------------------------------------------------------------------
    # Final chunk — full evaluation pipeline
    # ------------------------------------------------------------------

    # Concatenate audio
    full_wav = media_processor.concatenate_audio_chunks(session.current_chunk_buffer)

    # Transcribe
    transcript = stt_service.transcribe_audio(full_wav)
    if not transcript:
        logger.warning("STT returned empty transcript for session %s", session_id)

    # Retrieve question context from chat history
    last_question: dict = {}
    if session.gemini_chat_history:
        last_question = session.gemini_chat_history[-1].get("content", {})

    question_text = last_question.get("question_text", "")
    topic_area = last_question.get("topic_area", "")
    job_role = session.job_role

    # Evaluate
    gemini_start = time.monotonic()
    try:
        eval_dict = gemini_service.evaluate_answer(
            job_role,
            question_text,
            topic_area,
            transcript,
            session.current_round,
            session.total_rounds,
        )
    except NotImplementedError:
        eval_dict = _FALLBACK_EVAL
    gemini_latency_ms = int((time.monotonic() - gemini_start) * 1000)

    # Determine next_action
    probe_needed: bool = eval_dict.get("probe_needed", False)
    probe_question_dict: dict | None = eval_dict.get("probe_question")

    if probe_needed and probe_question_dict:
        # Follow-up probe — don't increment round
        next_action = NextAction(
            type="follow_up_probe",
            current_round=session.current_round,
            question=QuestionPayload(
                text=probe_question_dict.get("question_text", ""),
                type=probe_question_dict.get("question_type", "follow_up_probe"),
                topic_area=probe_question_dict.get("topic_area", topic_area),
            ),
        )
        response_status = "answer_evaluated"
        operations.append(OperationLog(op="probe_triggered", reason="memorization_detected"))

        # Store probe question in chat history
        session.gemini_chat_history.append({"role": "model", "content": probe_question_dict})

    elif session.current_round >= session.total_rounds:
        # Interview complete
        try:
            gemini_service.generate_final_summary(
                job_role,
                session.transcript_history,
                session.cumulative_scores,
            )
        except NotImplementedError:
            pass

        session.status = "completed"
        next_action = NextAction(
            type="complete",
            current_round=session.current_round,
            message="Interview complete. Retrieve results via GET /results/{session_id}.",
        )
        response_status = "interview_complete"

    else:
        # Advance to next round
        session.current_round += 1
        covered_topics = [
            r.topic_area for r in session.transcript_history if hasattr(r, "topic_area")
        ]
        _FALLBACK_NEXT_Q = {
            "question_text": "Tell me about a challenging technical problem you solved recently.",
            "topic_area": "Problem Solving",
            "question_type": "initial",
            "difficulty": "medium",
        }
        try:
            next_q_dict = gemini_service.generate_initial_question(
                job_role,
                current_round=session.current_round,
                total_rounds=session.total_rounds,
                covered_topics=covered_topics,
                transcript_history=session.transcript_history,
            )
        except (NotImplementedError, AttributeError):
            next_q_dict = _FALLBACK_NEXT_Q

        session.gemini_chat_history.append({"role": "model", "content": next_q_dict})
        next_action = NextAction(
            type="next_question",
            current_round=session.current_round,
            question=QuestionPayload(
                text=next_q_dict.get("question_text", ""),
                type=next_q_dict.get("question_type", "initial"),
                topic_area=next_q_dict.get("topic_area", ""),
            ),
        )
        response_status = "answer_evaluated"

    # Build RoundRecord and append to transcript history
    round_record = RoundRecord(
        round=session.current_round if not probe_needed else session.current_round,
        topic_area=topic_area,
        question=question_text,
        question_type=last_question.get("question_type", "initial"),
        transcript=transcript,
        scores=eval_dict.get("scores", {}),
        flags=eval_dict.get("flags", {}),
        evaluator_notes=eval_dict.get("evaluator_notes", ""),
    )
    session.transcript_history.append(round_record)

    # Update cumulative scores (simple average across all rounds so far)
    all_scores: list[dict] = [r.scores for r in session.transcript_history if r.scores]
    if all_scores:
        keys = all_scores[0].keys()
        session.cumulative_scores = {
            k: int(sum(s.get(k, 0) for s in all_scores) / len(all_scores))
            for k in keys
        }

    # Clear chunk buffer
    session.current_chunk_buffer = []

    # Add transcription and evaluation ops
    word_count = len(transcript.split()) if transcript else 0
    operations.append(OperationLog(op="audio_transcribed", word_count=word_count))
    operations.append(OperationLog(op="gemini_evaluated", latency_ms=gemini_latency_ms))

    # Persist session
    session_store.update_session(
        session_id,
        current_round=session.current_round,
        current_chunk_buffer=session.current_chunk_buffer,
        transcript_history=session.transcript_history,
        cumulative_scores=session.cumulative_scores,
        gemini_chat_history=session.gemini_chat_history,
        status=session.status,
        flags=session.flags,
    )

    # Cleanup temp files
    media_processor.cleanup_temp_files(session_id)

    # Build evaluation result
    evaluation = EvaluationResult(
        scores=EvaluationScores.model_validate(eval_dict["scores"]),
        flags=EvaluationFlags(**eval_dict["flags"]),
        evaluator_notes=eval_dict.get("evaluator_notes", ""),
    )

    return ChunkResponse(
        session_id=session_id,
        chunk_index=chunk_index,
        status=response_status,
        transcript=transcript,
        evaluation=evaluation,
        next_action=next_action,
        operations=operations,
    )


# ---------------------------------------------------------------------------
# GET /results/{session_id}
# ---------------------------------------------------------------------------

GCS_BUCKET = os.getenv("GCS_BUCKET", "karna-vault")


@app.get("/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str):
    # 1. Validate session exists
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Session not found", "session_id": session_id},
        )

    # 2. Session must be completed
    if session.status != "completed":
        return JSONResponse(
            status_code=409,
            content={
                "error": "Interview still in progress. Cannot retrieve results until session is complete.",
                "session_id": session_id,
                "current_round": session.current_round,
                "total_rounds": session.total_rounds,
            },
        )

    # 3. Compute overall_score — average of all 5 dimension scores
    cumulative = session.cumulative_scores
    _DEFAULT_SCORES = {
        "system_design": 0,
        "problem_solving": 0,
        "communication_clarity": 0,
        "depth_of_knowledge": 0,
        "adaptability": 0,
    }
    # Normalise keys (Gemini may use title-case keys)
    _alias_map = {
        "System Design": "system_design",
        "Problem Solving": "problem_solving",
        "Communication Clarity": "communication_clarity",
        "Depth of Knowledge": "depth_of_knowledge",
        "Adaptability": "adaptability",
    }
    normalised = {_alias_map.get(k, k): v for k, v in cumulative.items()}
    merged = {**_DEFAULT_SCORES, **normalised}
    score_values = list(merged.values())
    overall_score = int(sum(score_values) / len(score_values)) if score_values else 0

    # 4. Recommendation tier
    if overall_score >= 75:
        recommendation = "Strong"
    elif overall_score >= 50:
        recommendation = "Moderate"
    else:
        recommendation = "Weak"

    # 5. skill_scores
    skill_scores = EvaluationScores.model_validate(cumulative if cumulative else _DEFAULT_SCORES)

    # 6. flags
    flags = EvaluationFlags(
        memorization_detected=session.flags.get("memorization_count", 0) > 0,
        answer_quality="completed",
    )

    # 7. round_details
    round_details: list[RoundDetail] = []
    for record in session.transcript_history:
        # scores — handle empty dict gracefully
        record_scores_raw = record.scores if record.scores else {}
        try:
            record_scores = EvaluationScores.model_validate(record_scores_raw)
        except Exception:
            record_scores = EvaluationScores.model_validate(_DEFAULT_SCORES)

        # flags — handle missing keys gracefully
        record_flags_raw = record.flags if record.flags else {}
        try:
            record_flags = EvaluationFlags(
                memorization_detected=record_flags_raw.get("memorization_detected", False),
                answer_quality=record_flags_raw.get("answer_quality", "unknown"),
            )
        except Exception:
            record_flags = EvaluationFlags(memorization_detected=False, answer_quality="unknown")

        round_details.append(
            RoundDetail(
                round=getattr(record, "round", None),
                topic_area=getattr(record, "topic_area", None),
                question=record.question,
                question_type=record.question_type,
                transcript=record.transcript,
                scores=record_scores,
                flags=record_flags,
                evaluator_notes=record.evaluator_notes,
                follow_ups=[],
            )
        )

    # 8. summary — last gemini_chat_history entry with a "summary" key
    summary = "Interview complete. No summary available."
    for entry in reversed(session.gemini_chat_history):
        content = entry.get("content", {})
        if isinstance(content, dict) and "summary" in content:
            summary = content["summary"]
            break

    # 9. video_vault_manifest
    total_chunks = len(session.transcript_history)
    video_vault_manifest = VideoVaultManifest(
        bucket=GCS_BUCKET,
        prefix=f"{session_id}/",
        total_chunks=total_chunks,
        note="Video sealed. Not accessed by any AI model.",
    )

    return ResultsResponse(
        session_id=session_id,
        job_role=session.job_role,
        status="completed",
        overall_score=overall_score,
        recommendation=recommendation,
        skill_scores=skill_scores,
        flags=flags,
        round_details=round_details,
        summary=summary,
        video_vault_manifest=video_vault_manifest,
    )
