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

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from openboson.bank_loader import merge_banks
from openboson.bank_schema import ExamBank, Question, QuestionPool, QuestionType
from openboson.exsim.blueprint import (
    BLUEPRINTS,
    ExamBlueprint,
    InsufficientPoolError,
    bank_from_blueprint,
    build_exam_from_blueprint,
    get_blueprint,
    list_blueprints,
)
from openboson.exsim.scoring import ExamResult, score_exam
from openboson.exsim.session import ExamMode, ExamSession, QuestionPresentation
from openboson.registry import get_registry

_ROUTER = APIRouter(prefix="/api/v1", tags=["exsim"])

# Loaded raw banks (library data). Not startable as mega-exams.
_BANKS: dict[str, ExamBank] = {}
# Merged question pool used for blueprint sampling.
_POOL: QuestionPool | None = None
# Active sessions, keyed by session_id.
_SESSIONS: dict[str, ExamSession] = {}

# Unambiguous exam-code aliases → blueprint id (never raw pool codes).
_CODE_ALIASES: dict[str, str] = {
    "200-301": "ccna-200-301",
    "350-401": "encor-350-401",
}


def clear_content_cache() -> None:
    """Drop cached banks/pool so the next request reloads from the registry."""
    global _POOL
    _BANKS.clear()
    _POOL = None


def _load_default_banks() -> None:
    """Pre-load banks / pool from the content registry if not already loaded."""
    global _POOL
    if _BANKS and _POOL is not None:
        return
    reg = get_registry()
    banks = reg.banks()
    if not banks:
        return
    for bank in banks:
        _BANKS[bank.code] = bank
    _POOL = reg.question_pool()
    # Keep a merged synthetic bank for library lookups only.
    pool = merge_banks(list(_BANKS.values()))
    _BANKS.setdefault(
        "pool",
        ExamBank(
            title="OpenBoson Question Pool",
            code="pool",
            version="v1",
            provider="openboson",
            description="Merged question pool (library only)",
            topics=pool.topics or list(next(iter(_BANKS.values())).topics),
            questions=pool.questions,
        ),
    )


def _resolve_blueprint(exam_id: str) -> ExamBlueprint:
    """Resolve an exam id / alias to an enabled blueprint.

    Raw pool codes (e.g. ``pool-ccna``) are library data and are not startable.
    """
    if exam_id in BLUEPRINTS:
        bp = BLUEPRINTS[exam_id]
    elif exam_id in _CODE_ALIASES:
        bp = get_blueprint(_CODE_ALIASES[exam_id])
    else:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Exam {exam_id!r} not found. Start exams via blueprint IDs "
                f"(e.g. ccna-200-301) or unambiguous codes (200-301, 350-401)."
            ),
        )
    if not bp.enabled:
        raise HTTPException(
            status_code=400,
            detail=bp.coming_soon_label or f"{bp.title} is not available yet",
        )
    return bp


def _choices_for_display(
    q: Question, presentation: QuestionPresentation | None
) -> list[dict[str, Any]]:
    by_id = {c.id: c for c in (q.choices or [])}
    if presentation and presentation.choice_ids:
        order = presentation.choice_ids
    else:
        order = list(by_id.keys())
    out: list[dict[str, Any]] = []
    for cid in order:
        c = by_id.get(cid)
        if c is None:
            continue
        out.append({"id": c.id, "text": c.text, "media_url": c.media_url})
    return out


def _serialize_question_for_display(
    q: Question,
    presentation: QuestionPresentation | None = None,
) -> dict[str, Any]:
    """Render a question for the client WITHOUT leaking the correct answer."""
    base: dict[str, Any] = {
        "id": q.id,
        "type": q.type.value,
        "topic_code": q.topic_code,
        "difficulty": q.difficulty,
        "stem": q.stem,
        "media_url": q.media_url,
    }
    if q.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE):
        base["choices"] = _choices_for_display(q, presentation)
    if q.type == QuestionType.DRAG_MATCH:
        # Independently shuffled left/right with opaque IDs — never canonical pairs.
        if presentation and presentation.drag_left is not None:
            base["left_items"] = [d.to_dict() for d in presentation.drag_left]
            base["right_items"] = [
                d.to_dict() for d in (presentation.drag_right or [])
            ]
        else:
            # Fallback without session presentation: shuffle but do not pair.
            from openboson.exsim.session import build_question_presentation

            fallback = build_question_presentation(q)
            base["left_items"] = [d.to_dict() for d in (fallback.drag_left or [])]
            base["right_items"] = [d.to_dict() for d in (fallback.drag_right or [])]
    if q.type == QuestionType.ORDERED_LIST:
        if presentation and presentation.ordered_items is not None:
            base["ordered_items"] = list(presentation.ordered_items)
        else:
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
    """List startable blueprint exams (not raw question pools)."""
    _load_default_banks()
    items: list[dict[str, Any]] = []
    for bp in list_blueprints():
        if not bp.enabled:
            items.append(
                {
                    "id": bp.id,
                    "title": bp.title,
                    "code": bp.code,
                    "version": bp.version,
                    "provider": "openboson",
                    "description": bp.coming_soon_label or "Coming soon",
                    "pass_score": bp.pass_score,
                    "time_limit_minutes": bp.time_limit_minutes,
                    "question_count": bp.question_count,
                    "enabled": False,
                    "blueprint_id": bp.id,
                }
            )
            continue
        items.append(
            {
                "id": bp.id,
                "title": bp.title,
                "code": bp.code,
                "version": bp.version,
                "provider": "openboson",
                "description": f"Blueprint exam ({bp.id})",
                "pass_score": bp.pass_score,
                "time_limit_minutes": bp.time_limit_minutes,
                "question_count": bp.question_count,
                "enabled": True,
                "blueprint_id": bp.id,
            }
        )
    return items


@_ROUTER.post("/exams/{exam_id}/sessions")
def create_session(exam_id: str, body: CreateSessionRequest) -> dict[str, Any]:
    _load_default_banks()
    blueprint = _resolve_blueprint(exam_id)
    if _POOL is None:
        raise HTTPException(status_code=503, detail="Question pool not loaded")
    try:
        questions = build_exam_from_blueprint(_POOL.questions, blueprint)
    except InsufficientPoolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bank = bank_from_blueprint(blueprint, questions)
    session = ExamSession.create(
        bank,
        mode=body.mode,
        shuffle=False,
        blueprint_id=blueprint.id,
        questions=questions,
    )
    _SESSIONS[session.session_id] = session
    q = session.current_question
    return {
        "session_id": session.session_id,
        "exam_code": bank.code,
        "blueprint_id": blueprint.id,
        "mode": session.mode.value,
        "total_questions": len(session.questions),
        "question": _serialize_question_for_display(
            q, session.presentation_for(q.id)
        ),
    }


@_ROUTER.get("/sessions/{session_id}/questions/{index}")
def get_question(session_id: str, index: int) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not (0 <= index < len(session.questions)):
        raise HTTPException(status_code=400, detail="Index out of range")
    q = session.questions[index]
    return _serialize_question_for_display(q, session.presentation_for(q.id))


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
    response: dict[str, Any] = {
        "session_id": session_id,
        "question_id": body.question_id,
        "accepted": True,
    }
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
        pres = session.presentation_for(q.id)
        item: dict[str, Any] = {
            "question_id": q.id,
            "topic_code": q.topic_code,
            "type": q.type.value,
            "stem": q.stem,
            "choices": _choices_for_display(q, pres) if q.choices else [],
            "correct": correct.model_dump(),
            "user_answer": user_ans.answer if user_ans is not None else None,
            "is_correct": bool(user_ans.is_correct) if user_ans is not None else False,
            "explanation": q.explanation,
        }
        items.append(item)
    return {
        "session_id": session_id,
        "exam_code": session.exam.code,
        "blueprint_id": session.blueprint_id,
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
