"""Export finished exam score/review to JSON, CSV, and HTML.

Redacted mode omits correct answers and per-question correctness so shared
reports cannot leak keys. Exports do not include teaching explanations.
"""

from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path
from typing import Any, Literal

from openboson.exsim.scoring import ExamResult, score_exam
from openboson.exsim.session import ExamSession

ExportFormat = Literal["json", "csv", "html"]


def build_export_payload(
    session: ExamSession,
    result: ExamResult | None = None,
    *,
    redacted: bool = False,
) -> dict[str, Any]:
    """Build a serializable review payload for export."""
    if result is None:
        result = score_exam(session)
    domains = {
        prefix: {
            "domain_prefix": d.domain_prefix,
            "total": d.total,
            "correct": d.correct,
            "weight": d.weight,
            "percent": round(d.percent, 4),
        }
        for prefix, d in result.domain_breakdown.items()
    }
    items: list[dict[str, Any]] = []
    for q in session.questions:
        user_ans = session.answers.get(q.id)
        item: dict[str, Any] = {
            "question_id": q.id,
            "topic_code": q.topic_code,
            "type": q.type.value,
            "stem": q.stem,
            "user_answer": user_ans.answer if user_ans is not None else None,
        }
        if not redacted:
            correct = q.correct_answer_model
            item["correct"] = correct.model_dump()
            item["is_correct"] = bool(user_ans.is_correct) if user_ans is not None else False
            if q.choices:
                item["choices"] = [{"id": c.id, "text": c.text} for c in q.choices]
        items.append(item)

    summary: dict[str, Any] = {
        "session_id": result.session_id,
        "exam_code": result.exam_code,
        "exam_version": result.exam_version,
        "exam_title": session.exam.title,
        "mode": result.mode,
        "total_questions": result.total_questions,
        "correct_count": result.correct_count if not redacted else None,
        "incorrect_count": result.incorrect_count if not redacted else None,
        "unanswered_count": result.unanswered_count,
        "score": result.score,
        "score_percent": result.score_percent,
        "passing_score": result.passing_score,
        "passed": result.passed,
        "domain_breakdown": domains,
        "redacted": redacted,
        "items": items,
    }
    if redacted:
        for d in summary["domain_breakdown"].values():
            d.pop("correct", None)
            d["percent"] = round(d["percent"], 4)
        summary.pop("correct_count", None)
        summary.pop("incorrect_count", None)
    return summary


def to_json(
    session: ExamSession, result: ExamResult | None = None, *, redacted: bool = False
) -> str:
    payload = build_export_payload(session, result, redacted=redacted)
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def to_csv(
    session: ExamSession, result: ExamResult | None = None, *, redacted: bool = False
) -> str:
    payload = build_export_payload(session, result, redacted=redacted)
    buf = io.StringIO()
    fieldnames = [
        "question_id",
        "topic_code",
        "type",
        "stem",
        "user_answer",
    ]
    if not redacted:
        fieldnames.extend(["is_correct", "correct"])
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for item in payload["items"]:
        row = dict(item)
        row["user_answer"] = json.dumps(item.get("user_answer"), default=str)
        if not redacted:
            row["correct"] = json.dumps(item.get("correct"), default=str)
            row["is_correct"] = item.get("is_correct")
        writer.writerow(row)
    return buf.getvalue()


def to_html(
    session: ExamSession, result: ExamResult | None = None, *, redacted: bool = False
) -> str:
    payload = build_export_payload(session, result, redacted=redacted)
    title = html.escape(str(payload.get("exam_title") or payload["exam_code"]))
    verdict = "PASSED" if payload["passed"] else "FAILED"
    score = payload["score_percent"]
    pass_mark = int(payload["passing_score"] * 100)
    redacted_note = "<p><em>Redacted export — correct answers omitted.</em></p>" if redacted else ""
    domain_rows = []
    for prefix, d in payload["domain_breakdown"].items():
        pct = int(d["percent"] * 100)
        if redacted:
            domain_rows.append(f"<tr><td>{html.escape(prefix)}</td><td>{pct}%</td></tr>")
        else:
            domain_rows.append(
                f"<tr><td>{html.escape(prefix)}</td>"
                f"<td>{pct}% ({d.get('correct', 0)}/{d['total']})</td></tr>"
            )
    item_blocks = []
    for i, item in enumerate(payload["items"], start=1):
        stem = html.escape(item["stem"])
        user = html.escape(json.dumps(item.get("user_answer"), default=str))
        extra = ""
        if not redacted:
            correct = html.escape(json.dumps(item.get("correct"), default=str))
            ok = "correct" if item.get("is_correct") else "incorrect"
            extra = (
                f"<p><strong>Result:</strong> {ok}</p>"
                f"<p><strong>Correct:</strong> <code>{correct}</code></p>"
            )
        item_blocks.append(
            f"<section><h3>Q{i}. {html.escape(item['question_id'])}</h3>"
            f"<p>{stem}</p>"
            f"<p><strong>Your answer:</strong> <code>{user}</code></p>"
            f"{extra}</section>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>OpenBoson — {title}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; }}
h1 {{ margin-bottom: 0.25rem; }}
table {{ border-collapse: collapse; margin: 1rem 0; }}
td, th {{ border: 1px solid #ccc; padding: 0.4rem 0.75rem; }}
section {{ border-top: 1px solid #ddd; padding: 1rem 0; }}
code {{ background: #f4f4f4; padding: 0.1rem 0.3rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>{html.escape(payload["exam_code"])} {html.escape(payload["exam_version"])} — {verdict}</p>
<p>Score: {score:.1f}% (pass mark {pass_mark}%)</p>
{redacted_note}
<h2>Domain breakdown</h2>
<table>
<tr><th>Domain</th><th>Accuracy</th></tr>
{"".join(domain_rows)}
</table>
<h2>Questions</h2>
{"".join(item_blocks)}
</body>
</html>
"""


def export_text(
    session: ExamSession,
    fmt: ExportFormat,
    result: ExamResult | None = None,
    *,
    redacted: bool = False,
) -> str:
    if fmt == "json":
        return to_json(session, result, redacted=redacted)
    if fmt == "csv":
        return to_csv(session, result, redacted=redacted)
    if fmt == "html":
        return to_html(session, result, redacted=redacted)
    raise ValueError(f"Unsupported export format: {fmt}")


def write_export(
    path: str | Path,
    session: ExamSession,
    fmt: ExportFormat,
    result: ExamResult | None = None,
    *,
    redacted: bool = False,
) -> Path:
    out = Path(path)
    out.write_text(export_text(session, fmt, result, redacted=redacted), encoding="utf-8")
    return out
