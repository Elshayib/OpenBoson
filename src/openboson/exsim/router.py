"""FastAPI router exposing ExSim endpoints.

The router keeps a module-level registry of active sessions (in-memory; a
future task will persist via openboson.db). The HTTP surface is convenient
for tests and the eventual web UI; the PySide6 GUI calls engine modules
directly.

Endpoints (all under ``/api/v1``):
    GET    /exams
    POST   /exams/{exam_id}/sessions
    GET    /sessions/{session_id}/questions/{index}
    POST   /sessions/{session_id}/answers
    POST   /sessions/{session_id}/bookmark
    POST   /sessions/{session_id}/finish
    GET    /sessions/{session_id}/review
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from openboson.bank_loader import load_exam_bank
from openboson.bank_schema import ExamBank, Question, QuestionType
from openboson.exsim.scoring import ExamResult, score_exam
from openboson.bank_loader import load_banks_from_dir, merge_banks
from openboson.exsim.session import ExamMode, ExamSession

# Module-level state for MVP. A future task will replace this with a
# registry that reads from data/ and persists sessions to SQLite.
_ROUTER = APIRouter(prefix="/api/v1", tags=["exsim"])

# Loaded banks, keyed by exam code (e.g. "200-301").
_BANKS: dict[str, ExamBank] = {}
# Active sessions, keyed by session_id.
_SESSIONS: dict[str, ExamSession] = {}

# Default banks shipped with the repo. The router preloads them lazily.
# Path: src/openboson/exsim/router.py -> repo root (parents[3]) -> data/demo_banks
_DEFAULT_BANKS_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "demo_banks"
)


def _load_default_banks() -> None:
    """Pre-load the bundled demo banks if not already loaded."""
    if _BANKS:
        return
    if not _DEFAULT_BANKS_DIR.is_dir():
        return
    for bank in load_banks_from_dir(_DEFAULT_BANKS_DIR):
        # Prefer unique codes; if duplicates, later files overwrite.
        _BANKS[bank.code] = bank
    # Also expose a merged pool under a stable key for clients that want all Qs.
    if _BANKS:
        pool = merge_banks(list(_BANKS.values()))
        # Synthetic bank wrapper for listing; only used if no single bank matches.
        _BANKS.setdefault(
            "pool",
            ExamBank(
                title="OpenBoson Question Pool",
                code="pool",
                version="v1",
                provider="openboson",
                description="Merged question pool",
                topics=pool.topics or list(next(iter(_BANKS.values())).topics),
                questions=pool.questions,
            ),
        )


def _serialize_question_for_display(q: Question) -> dict[str, Any]:
    """Render a question for the client WITHOUT leaking the correct answer."""
    base = {
        "id": q.id,
        "type": q.type.value,
        "topic_code": q.topic_code,
        "difficulty": q.difficulty,
        "stem": q.stem,
        "media_url": q.media_url,
    }
    if q.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
        base["choices"] = [
            {"id": c.id, "text": c.text, "media_url": c.media_url} for c in (q.choices or [])
        ]
    if q.type == QuestionType.DRAG_MATCH:
        base["drag_pairs"] = [{"left": p.left, "right": p.right} for p in (q.drag_pairs or [])]
    if q.type == QuestionType.ORDERED_LIST:
        base["ordered_items"] = list(q.ordered_items or [])
    if q.type == QuestionType.SIM and q.sim is not None:
        base["sim"] = {
            "instructions": q.sim.instructions,
            "topology_ref": q.sim.topology_ref,
        }
    return base


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ExamMode = ExamMode.EXAM


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    answer: Any
    time_spent_seconds: float = 0.0


class BookmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str


@_ROUTER.get("/exams")
def list_exams() -> list[dict[str, Any]]:
    _load_default_banks()
    return [
        {
            "id": code,
            "title": bank.title,
            "code": bank.code,
            "version": bank.version,
            "provider": bank.provider,
            "description": bank.description,
            "pass_score": bank.pass_score,
            "time_limit_minutes": bank.time_limit_minutes,
            "question_count": len(bank.questions),
        }
        for code, bank in _BANKS.items()
    ]


@_ROUTER.post("/exams/{exam_id}/sessions")
def create_session(exam_id: str, body: CreateSessionRequest) -> dict[str, Any]:
    _load_default_banks()
    bank = _BANKS.get(exam_id)
    if bank is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found")
    session = ExamSession.create(bank, mode=body.mode)
    _SESSIONS[session.session_id] = session
    return {
        "session_id": session.session_id,
        "exam_code": bank.code,
        "mode": session.mode.value,
        "total_questions": len(session.questions),
        "question": _serialize_question_for_display(session.current_question),
    }


@_ROUTER.get("/sessions/{session_id}/questions/{index}")
def get_question(session_id: str, index: int) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not (0 <= index < len(session.questions)):
        raise HTTPException(status_code=400, detail="Index out of range")
    q = session.questions[index]
    return _serialize_question_for_display(q)


@_ROUTER.post("/sessions/{session_id}/answers")
def submit_answer(session_id: str, body: SubmitAnswerRequest) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    q = next((qq for qq in session.questions if qq.id == body.question_id), None)
    if q is None:
        raise HTTPException(status_code=400, detail="Question not part of this session")
    graded = session.submit_answer(
        body.question_id, body.answer, time_spent_seconds=body.time_spent_seconds
    )
    response = {"session_id": session_id, "question_id": body.question_id, "accepted": True}
    if graded is not None:
        response["is_correct"] = graded
    return response


@_ROUTER.post("/sessions/{session_id}/bookmark")
def toggle_bookmark(session_id: str, body: BookmarkRequest) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    new_state = session.toggle_bookmark(body.question_id)
    return {"session_id": session_id, "question_id": body.question_id, "bookmarked": new_state}


@_ROUTER.post("/sessions/{session_id}/finish")
def finish_session(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.finish()
    result = score_exam(session)
    return _serialize_exam_result(result)


@_ROUTER.get("/sessions/{session_id}/review")
def review_session(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_finished():
        raise HTTPException(status_code=400, detail="Session not finished")
    result = score_exam(session)
    items = []
    for q in session.questions:
        user_ans = session.answers.get(q.id)
        correct = q.correct_answer_model
        items.append(
            {
                "question_id": q.id,
                "topic_code": q.topic_code,
                "type": q.type.value,
                "stem": q.stem,
                "choices": [
                    {"id": c.id, "text": c.text} for c in (q.choices or [])
                ],
                "correct": correct.model_dump(),
                "user_answer": user_ans.answer if user_ans is not None else None,
                "is_correct": bool(user_ans.is_correct) if user_ans is not None else False,
                "explanation": q.explanation,
            }
        )
    return {
        "session_id": session_id,
        "exam_code": session.exam.code,
        "result": _serialize_exam_result(result),
        "items": items,
    }


def _serialize_exam_result(result: ExamResult) -> dict[str, Any]:
    return {
        "session_id": result.session_id,
        "exam_code": result.exam_code,
        "exam_version": result.exam_version,
        "mode": result.mode,
        "total_questions": result.total_questions,
        "correct_count": result.correct_count,
        "incorrect_count": result.incorrect_count,
        "unanswered_count": result.unanswered_count,
        "score": result.score,
        "score_percent": result.score_percent,
        "passing_score": result.passing_score,
        "passed": result.passed,
        "domain_breakdown": {
            prefix: {
                "domain_prefix": d.domain_prefix,
                "total": d.total,
                "correct": d.correct,
                "weight": d.weight,
                "percent": d.percent,
                "weighted_percent": d.weighted_percent,
            }
            for prefix, d in result.domain_breakdown.items()
        },
        "question_results": result.question_results,
    }
