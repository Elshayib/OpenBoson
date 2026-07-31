"""FastAPI router exposing NetSim endpoints (mirrors the ExSim router)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from openboson.netsim.lab_schema import LabBank
from openboson.netsim.session import LabResult, LabSession, score_lab
from openboson.registry import get_registry

_ROUTER = APIRouter(prefix="/api/v1", tags=["netsim"])

_LABS: dict[str, LabBank] = {}
_SESSIONS: dict[str, LabSession] = {}


def clear_content_cache() -> None:
    """Drop cached labs so the next request reloads from the registry."""
    _LABS.clear()


def _load_default_labs() -> None:
    if _LABS:
        return
    for lab in get_registry().labs():
        _LABS[lab.lab_id] = lab


def _serialize_topology(lab: LabBank) -> dict[str, Any]:
    return {
        "devices": [
            {
                "name": d.name,
                "type": d.type.value,
                "interfaces": [
                    {"name": i.name, "ip": i.ip, "connected_to": i.connected_to}
                    for i in d.interfaces
                ],
            }
            for d in lab.topology.devices
        ],
        "links": [{"a": l.a, "b": l.b} for l in lab.topology.links],
    }


class CreateLabSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubmitConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: str


@_ROUTER.get("/labs")
def list_labs() -> list[dict[str, Any]]:
    _load_default_labs()
    return [
        {
            "id": lab.lab_id,
            "title": lab.title,
            "topic_code": lab.topic_code,
            "difficulty": lab.difficulty,
            "description": lab.description,
            "task_count": len(lab.tasks),
        }
        for lab in _LABS.values()
    ]


@_ROUTER.post("/labs/{lab_id}/sessions")
def create_lab_session(lab_id: str, _body: CreateLabSessionRequest | None = None) -> dict[str, Any]:
    _load_default_labs()
    lab = _LABS.get(lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"Lab {lab_id} not found")
    session = LabSession.create(lab)
    _SESSIONS[session.session_id] = session
    return {
        "session_id": session.session_id,
        "lab_id": lab.lab_id,
        "title": lab.title,
        "task_count": len(lab.tasks),
        "topology": _serialize_topology(lab),
        "task": _serialize_task(lab, session.current_task_index),
    }


@_ROUTER.get("/lab-sessions/{session_id}/task")
def get_current_task(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    lab = session.lab
    return {
        "session_id": session_id,
        "task_index": session.current_task_index,
        "task_count": len(lab.tasks),
        "task": _serialize_task(lab, session.current_task_index),
        "topology": _serialize_topology(lab),
    }


@_ROUTER.post("/lab-sessions/{session_id}/submit")
def submit_config(session_id: str, body: SubmitConfigRequest) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    grade = session.submit_task(body.config)
    # Advance to the next task automatically (Submit & Next), staying at the
    # last task if it was the final one.
    session.next_task()
    return {
        "session_id": session_id,
        "task_id": grade.task_id,
        "is_correct": grade.is_correct,
        "score": grade.score,
        "missing": grade.missing,
        "forbidden_found": grade.forbidden_found,
        "order_violations": grade.order_violations,
        "feedback": grade.feedback,
    }


@_ROUTER.post("/lab-sessions/{session_id}/reset")
def reset_lab_session(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.reset()
    lab = session.lab
    return {
        "session_id": session_id,
        "lab_id": lab.lab_id,
        "task_index": session.current_task_index,
        "task_count": len(lab.tasks),
        "task": _serialize_task(lab, session.current_task_index),
        "topology": _serialize_topology(lab),
    }


@_ROUTER.post("/lab-sessions/{session_id}/finish")
def finish_lab(session_id: str) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.finish()
    result = score_lab(session)
    return _serialize_lab_result(result)


def _serialize_task(lab: LabBank, index: int) -> dict[str, Any]:
    task = lab.tasks[index]
    return {
        "id": task.id,
        "index": index,
        "instructions": task.instructions,
        "expected_config": task.expected_config,
    }


def _serialize_lab_result(result: LabResult) -> dict[str, Any]:
    return {
        "session_id": result.session_id,
        "lab_id": result.lab_id,
        "lab_title": result.lab_title,
        "total_tasks": result.total_tasks,
        "passed_tasks": result.passed_tasks,
        "score": result.score,
        "score_percent": result.score * 100.0,
        "task_grades": {
            tid: {
                "is_correct": g.is_correct,
                "score": g.score,
                "missing": g.missing,
                "forbidden_found": g.forbidden_found,
                "feedback": g.feedback,
            }
            for tid, g in result.task_grades.items()
        },
    }
