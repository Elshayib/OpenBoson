"""FastAPI router exposing ExSim endpoints.

Active sessions are kept in memory for low-latency access and mirrored to
SQLite via ``session_store`` so pause/resume survives process restart.

Endpoints (all under ``/api/v1``):
    GET    /exams
    POST   /exams/{exam_id}/sessions
    GET    /blueprints/{blueprint_id}/coverage
    GET    /custom-exams/presets
    POST   /custom-exams/presets
    DELETE /custom-exams/presets/{preset_id}
    POST   /custom-exams/preview
    POST   /custom-exams/sessions
    GET    /sessions
    GET    /sessions/{session_id}
    GET    /sessions/{session_id}/questions/{index}
    POST   /sessions/{session_id}/answers
    POST   /sessions/{session_id}/bookmark
    POST   /sessions/{session_id}/mark
    POST   /sessions/{session_id}/pause
    POST   /sessions/{session_id}/resume
    POST   /sessions/{session_id}/finish
    GET    /sessions/{session_id}/review
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from openboson.bank_loader import merge_banks
from openboson.bank_schema import ExamBank, Question, QuestionPool, QuestionType
from openboson.exsim import session_store
from openboson.exsim.blueprint import (
    BLUEPRINTS,
    ExamBlueprint,
    InsufficientPoolError,
    bank_from_blueprint,
    build_exam_from_blueprint,
    coverage_for_blueprint,
    get_blueprint,
    list_blueprints,
)
from openboson.exsim.custom_exam import (
    CustomExamSpec,
    bank_from_custom,
    build_exam_from_custom,
    coverage_for_custom,
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
            base["right_items"] = [d.to_dict() for d in (presentation.drag_right or [])]
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


class MarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str


class PauseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remaining_seconds: int | None = None


class CustomExamStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ExamMode = ExamMode.EXAM
    preset_id: str | None = None
    spec: dict[str, Any] | None = None


class CustomExamPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_id: str | None = None
    spec: dict[str, Any] | None = None


def _pool_by_id() -> dict[str, Question]:
    _load_default_banks()
    if _POOL is None:
        return {}
    return _POOL.by_id()


def _persist(session: ExamSession) -> None:
    if session.is_finished():
        return
    import contextlib

    with contextlib.suppress(Exception):
        # Persistence must not break the HTTP surface in tests / headless use.
        session_store.upsert_active_session(session)


def _get_session(session_id: str) -> ExamSession:
    session = _SESSIONS.get(session_id)
    if session is not None:
        return session
    by_id = _pool_by_id()
    restored = session_store.load_active_session(by_id, engine_session_id=session_id)
    if restored is None:
        restored = session_store.load_session_by_id(by_id, session_id)
    if restored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _SESSIONS[restored.session_id] = restored
    return restored


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
    _persist(session)
    q = session.current_question
    return {
        "session_id": session.session_id,
        "exam_code": bank.code,
        "blueprint_id": blueprint.id,
        "mode": session.mode.value,
        "status": str(session.status),
        "remaining_seconds": session.remaining_seconds,
        "total_questions": len(session.questions),
        "question": _serialize_question_for_display(q, session.presentation_for(q.id)),
    }


@_ROUTER.get("/sessions")
def list_sessions() -> list[dict[str, Any]]:
    """List resumable (in-progress / paused) sessions."""
    items = []
    for info in session_store.list_resumable_sessions():
        items.append(
            {
                "session_id": info.engine_session_id,
                "exam_code": info.exam_code,
                "exam_version": info.exam_version,
                "exam_title": info.exam_title,
                "status": info.status,
                "current_index": info.current_index,
                "question_count": info.question_count,
                "answered_count": info.answered_count,
                "remaining_seconds": info.remaining_seconds,
                "blueprint_id": info.blueprint_id,
            }
        )
    return items


@_ROUTER.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    return {
        "session_id": session.session_id,
        "exam_code": session.exam.code,
        "exam_version": session.exam.version,
        "blueprint_id": session.blueprint_id,
        "mode": session.mode.value,
        "status": str(session.status),
        "current_index": session.current_index,
        "total_questions": len(session.questions),
        "answered_count": session.answered_count(),
        "remaining_seconds": session.remaining_seconds,
        "bookmarked": sorted(session.bookmarked),
        "marked_for_review": sorted(session.marked_for_review),
    }


@_ROUTER.get("/sessions/{session_id}/questions/{index}")
def get_question(session_id: str, index: int) -> dict[str, Any]:
    session = _get_session(session_id)
    if not (0 <= index < len(session.questions)):
        raise HTTPException(status_code=400, detail="Index out of range")
    session.goto(index)
    _persist(session)
    q = session.questions[index]
    return _serialize_question_for_display(q, session.presentation_for(q.id))


@_ROUTER.post("/sessions/{session_id}/answers")
def submit_answer(session_id: str, body: SubmitAnswerRequest) -> dict[str, Any]:
    session = _get_session(session_id)
    q = next((qq for qq in session.questions if qq.id == body.question_id), None)
    if q is None:
        raise HTTPException(status_code=400, detail="Question not part of this session")
    graded = session.submit_answer(
        body.question_id, body.answer, time_spent_seconds=body.time_spent_seconds
    )
    _persist(session)
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
    session = _get_session(session_id)
    new_state = session.toggle_bookmark(body.question_id)
    _persist(session)
    return {"session_id": session_id, "question_id": body.question_id, "bookmarked": new_state}


@_ROUTER.post("/sessions/{session_id}/mark")
def toggle_mark(session_id: str, body: MarkRequest) -> dict[str, Any]:
    session = _get_session(session_id)
    new_state = session.toggle_mark_for_review(body.question_id)
    _persist(session)
    return {
        "session_id": session_id,
        "question_id": body.question_id,
        "marked_for_review": new_state,
    }


@_ROUTER.post("/sessions/{session_id}/pause")
def pause_session(session_id: str, body: PauseRequest | None = None) -> dict[str, Any]:
    session = _get_session(session_id)
    remaining = body.remaining_seconds if body is not None else session.remaining_seconds
    try:
        session.pause(remaining)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _persist(session)
    return {
        "session_id": session_id,
        "status": str(session.status),
        "remaining_seconds": session.remaining_seconds,
    }


@_ROUTER.post("/sessions/{session_id}/resume")
def resume_session(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    try:
        session.resume()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _persist(session)
    return {
        "session_id": session_id,
        "status": str(session.status),
        "remaining_seconds": session.remaining_seconds,
        "current_index": session.current_index,
    }


@_ROUTER.post("/sessions/{session_id}/finish")
def finish_session(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
    session.finish()
    result = score_exam(session)
    try:
        from openboson import stats_service

        stats_service.save_exam_result(session, result)
    except Exception:
        pass
    _SESSIONS.pop(session_id, None)
    return _serialize_exam_result(result)


@_ROUTER.get("/sessions/{session_id}/review")
def review_session(session_id: str) -> dict[str, Any]:
    session = _get_session(session_id)
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


@_ROUTER.get("/blueprints/{blueprint_id}/coverage")
def blueprint_coverage(blueprint_id: str) -> dict[str, Any]:
    _load_default_banks()
    try:
        blueprint = get_blueprint(blueprint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if _POOL is None:
        raise HTTPException(status_code=503, detail="Question pool not loaded")
    cov = coverage_for_blueprint(_POOL.questions, blueprint)
    return {
        "blueprint_id": cov.blueprint_id,
        "counts": cov.counts,
        "required": cov.required,
        "ready": cov.ready,
        "deficits": cov.deficits,
    }


def _resolve_custom_spec(
    *,
    preset_id: str | None,
    spec: dict[str, Any] | None,
) -> tuple[CustomExamSpec, str | None]:
    from openboson.exsim import custom_exam_store

    if preset_id:
        preset = custom_exam_store.get_preset(preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail=f"Unknown preset: {preset_id}")
        exam_spec = CustomExamSpec.model_validate(
            preset.model_dump(exclude={"id", "created_at", "updated_at"})
        )
        return exam_spec, preset.id
    if spec is None:
        raise HTTPException(status_code=400, detail="Provide preset_id or spec")
    return CustomExamSpec.model_validate(spec), spec.get("id")


@_ROUTER.get("/custom-exams/presets")
def list_custom_presets() -> list[dict[str, Any]]:
    from openboson.exsim import custom_exam_store

    return [p.model_dump() for p in custom_exam_store.list_presets()]


@_ROUTER.post("/custom-exams/presets")
def save_custom_preset(body: dict[str, Any]) -> dict[str, Any]:
    from openboson.exsim import custom_exam_store

    try:
        saved = custom_exam_store.save_preset(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return saved.model_dump()


@_ROUTER.delete("/custom-exams/presets/{preset_id}")
def delete_custom_preset(preset_id: str) -> dict[str, Any]:
    from openboson.exsim import custom_exam_store

    ok = custom_exam_store.delete_preset(preset_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {preset_id}")
    return {"deleted": True, "id": preset_id}


@_ROUTER.post("/custom-exams/preview")
def preview_custom_exam(body: CustomExamPreviewRequest) -> dict[str, Any]:
    _load_default_banks()
    if _POOL is None:
        raise HTTPException(status_code=503, detail="Question pool not loaded")
    exam_spec, _preset_id = _resolve_custom_spec(preset_id=body.preset_id, spec=body.spec)
    history = None
    if exam_spec.history != "any":
        from openboson import stats_service

        history = stats_service.question_history_map()
    return coverage_for_custom(_POOL.questions, exam_spec, history=history)


@_ROUTER.post("/custom-exams/sessions")
def create_custom_session(body: CustomExamStartRequest) -> dict[str, Any]:
    _load_default_banks()
    if _POOL is None:
        raise HTTPException(status_code=503, detail="Question pool not loaded")
    exam_spec, preset_id = _resolve_custom_spec(preset_id=body.preset_id, spec=body.spec)
    history = None
    if exam_spec.history != "any":
        from openboson import stats_service

        history = stats_service.question_history_map()
    try:
        questions = build_exam_from_custom(_POOL.questions, exam_spec, history=history)
    except InsufficientPoolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bank = bank_from_custom(exam_spec, questions)
    session = ExamSession.create(
        bank,
        mode=body.mode,
        shuffle=False,
        questions=questions,
        seed=exam_spec.seed,
        custom_preset_id=preset_id,
    )
    _SESSIONS[session.session_id] = session
    _persist(session)
    q = session.current_question
    return {
        "session_id": session.session_id,
        "exam_code": bank.code,
        "custom_preset_id": preset_id,
        "mode": session.mode.value,
        "status": str(session.status),
        "remaining_seconds": session.remaining_seconds,
        "total_questions": len(session.questions),
        "question": _serialize_question_for_display(q, session.presentation_for(q.id)),
    }
