"""Tests for versioned SQLite migrations and exam/question identity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from openboson import stats_service
from openboson.bank_loader import load_exam_bank
from openboson.db import get_sessionmaker, init_db
from openboson.db_migrations import CURRENT_SCHEMA_VERSION, run_migrations
from openboson.exsim.scoring import score_exam
from openboson.exsim.session import ExamMode, ExamSession
from openboson.models import UserAnswer

FIXTURE = __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "sample_bank.yaml"


def _create_pre_migration_schema(engine: Engine) -> None:
    """Create the schema that existed before exam_code / bank_question_id."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    display_name VARCHAR(120) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exams (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    exam_code VARCHAR(40) NOT NULL,
                    version VARCHAR(20) NOT NULL,
                    provider VARCHAR(60) NOT NULL,
                    meta_json TEXT,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE questions (
                    id INTEGER NOT NULL PRIMARY KEY,
                    exam_id INTEGER NOT NULL,
                    topic_code VARCHAR(20) NOT NULL,
                    type VARCHAR(30) NOT NULL,
                    stem_json TEXT NOT NULL,
                    choices_json TEXT NOT NULL,
                    correct_answer_json TEXT NOT NULL,
                    explanation TEXT,
                    difficulty INTEGER NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exam_sessions (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    exam_id INTEGER,
                    mode VARCHAR(20) NOT NULL,
                    started_at DATETIME NOT NULL,
                    finished_at DATETIME,
                    score FLOAT,
                    passed BOOLEAN,
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE user_answers (
                    id INTEGER NOT NULL PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    question_id INTEGER,
                    answer_json TEXT NOT NULL,
                    is_correct BOOLEAN,
                    time_spent_seconds INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES exam_sessions (id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
                )
                """
            )
        )


def _seed_legacy_history(engine: Engine) -> None:
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (id, display_name, created_at) VALUES (1, 'Default', :t)"),
            {"t": now},
        )
        conn.execute(
            text(
                """
                INSERT INTO exams (id, title, exam_code, version, provider, created_at)
                VALUES (1, 'CCNA Demo', '200-301', 'v1.1', 'openboson', :t)
                """
            ),
            {"t": now},
        )
        conn.execute(
            text(
                """
                INSERT INTO exam_sessions (
                    id, user_id, exam_id, mode, started_at, finished_at, score, passed
                ) VALUES (1, 1, 1, 'exam', :t, :t, 0.9, 1)
                """
            ),
            {"t": now},
        )
        conn.execute(
            text(
                """
                INSERT INTO user_answers (
                    id, session_id, question_id, answer_json, is_correct, time_spent_seconds
                ) VALUES (1, 1, NULL, '[]', 1, 5)
                """
            )
        )
        # Orphan session with no Exam row (historically rendered as exam-None).
        conn.execute(
            text(
                """
                INSERT INTO exam_sessions (
                    id, user_id, exam_id, mode, started_at, finished_at, score, passed
                ) VALUES (2, 1, NULL, 'practice', :t, :t, 0.5, 0)
                """
            ),
            {"t": now},
        )


def _correct_answer(question):
    from openboson.bank_schema import QuestionType

    ca = question.correct_answer_model
    if question.type == QuestionType.SINGLE_CHOICE:
        return {"answer": ca.answer}
    if question.type == QuestionType.MULTIPLE_CHOICE:
        return {"answers": ca.answers}
    if question.type == QuestionType.DRAG_MATCH:
        return {"pairs": [{"left": p.left, "right": p.right} for p in ca.pairs]}
    if question.type == QuestionType.ORDERED_LIST:
        return {"order": ca.order}
    if question.type == QuestionType.SIM:
        return {"config": "\n".join(ca.expected_commands or [])}
    return {}


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    db = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db}", future=True)
    _create_pre_migration_schema(engine)
    _seed_legacy_history(engine)
    yield engine, db


def test_migration_backfills_exam_identity_and_preserves_history(legacy_db, monkeypatch):
    engine, _db = legacy_db
    init_db(engine)
    monkeypatch.setattr(stats_service, "_engine", engine)

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version FROM schema_version WHERE id = 1")).scalar()
        assert version == CURRENT_SCHEMA_VERSION
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info('exam_sessions')"))}
        assert "exam_code" in cols and "exam_version" in cols
        answer_cols = {r[1] for r in conn.execute(text("PRAGMA table_info('user_answers')"))}
        assert "bank_question_id" in answer_cols

        row = conn.execute(
            text("SELECT exam_code, exam_version FROM exam_sessions WHERE id = 1")
        ).one()
        assert row[0] == "200-301"
        assert row[1] == "v1.1"

        orphan = conn.execute(text("SELECT exam_code FROM exam_sessions WHERE id = 2")).scalar()
        assert orphan == ""

    history = stats_service.exam_history()
    codes = {h.exam_code for h in history}
    assert "200-301" in codes
    assert "exam-None" not in codes
    assert "unknown" in codes  # orphan session with no code / exam_id


def test_migration_then_new_save_keeps_question_ids(legacy_db, monkeypatch):
    engine, _db = legacy_db
    init_db(engine)
    monkeypatch.setattr(stats_service, "_engine", engine)

    bank = load_exam_bank(FIXTURE)
    sess = ExamSession.create(bank, mode=ExamMode.PRACTICE)
    for q in sess.questions:
        sess.submit_answer(q.id, _correct_answer(q), grade_now=True)
    result = score_exam(sess)
    row_id = stats_service.save_exam_result(sess, result)
    assert row_id > 0

    history = stats_service.exam_history()
    assert any(h.exam_code == bank.code for h in history)
    assert all(h.exam_code != "exam-None" for h in history)

    Session = get_sessionmaker(engine)
    with Session() as s:
        answers = s.query(UserAnswer).filter(UserAnswer.session_id == row_id).all()
        assert len(answers) == len(sess.questions)
        saved_ids = {a.bank_question_id for a in answers}
        assert saved_ids == {q.id for q in sess.questions}


def test_run_migrations_idempotent_on_fresh_db(tmp_path):
    db = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{db}", future=True)
    init_db(engine)
    v1 = run_migrations(engine)
    v2 = run_migrations(engine)
    assert v1 == CURRENT_SCHEMA_VERSION
    assert v2 == CURRENT_SCHEMA_VERSION
