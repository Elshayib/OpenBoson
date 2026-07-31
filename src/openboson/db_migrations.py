"""Versioned SQLite schema migrations for the local OpenBoson database.

Kept intentionally small (no Alembic) for the single-user desktop DB. Invoked
from ``init_db`` before normal ORM use.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

# Bump when adding a new migration function below.
CURRENT_SCHEMA_VERSION = 1

_SCHEMA_VERSION_TABLE = "schema_version"


def run_migrations(engine: Engine) -> int:
    """Apply pending migrations. Returns the schema version after running."""
    with engine.begin() as conn:
        _ensure_version_table(conn)
        version = _read_version(conn)
        for target, migrate in _MIGRATIONS:
            if version < target:
                logger.info("Applying DB migration v%s (from v%s)", target, version)
                migrate(conn)
                _write_version(conn, target)
                version = target
        # Fresh databases created via create_all already match CURRENT models;
        # stamp them so we do not re-run rebuilds on the next launch.
        if version < CURRENT_SCHEMA_VERSION:
            _write_version(conn, CURRENT_SCHEMA_VERSION)
            version = CURRENT_SCHEMA_VERSION
    return version


def _ensure_version_table(conn: Connection) -> None:
    conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {_SCHEMA_VERSION_TABLE} (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            )
            """
        )
    )


def _read_version(conn: Connection) -> int:
    row = conn.execute(text(f"SELECT version FROM {_SCHEMA_VERSION_TABLE} WHERE id = 1")).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _write_version(conn: Connection, version: int) -> None:
    existing = conn.execute(
        text(f"SELECT version FROM {_SCHEMA_VERSION_TABLE} WHERE id = 1")
    ).fetchone()
    if existing is None:
        conn.execute(
            text(f"INSERT INTO {_SCHEMA_VERSION_TABLE} (id, version) VALUES (1, :v)"),
            {"v": version},
        )
    else:
        conn.execute(
            text(f"UPDATE {_SCHEMA_VERSION_TABLE} SET version = :v WHERE id = 1"),
            {"v": version},
        )


def _table_exists(conn: Connection, name: str) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone()
    return row is not None


def _columns(conn: Connection, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return {r[1] for r in rows}


def _migrate_v1_exam_identity(conn: Connection) -> None:
    """Add exam_code/exam_version on sessions and bank_question_id on answers.

    Rebuilds SQLite tables when columns are missing so NOT NULL columns land
    correctly. Backfills exam identity from the ``exams`` table when possible.
    """
    if not _table_exists(conn, "exam_sessions"):
        return

    session_cols = _columns(conn, "exam_sessions")
    if "exam_code" not in session_cols or "exam_version" not in session_cols:
        _rebuild_exam_sessions(conn)

    if _table_exists(conn, "user_answers"):
        answer_cols = _columns(conn, "user_answers")
        if "bank_question_id" not in answer_cols:
            _rebuild_user_answers(conn)


def _rebuild_exam_sessions(conn: Connection) -> None:
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        text(
            """
            CREATE TABLE exam_sessions_new (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                exam_id INTEGER,
                exam_code VARCHAR(40) NOT NULL DEFAULT '',
                exam_version VARCHAR(20) NOT NULL DEFAULT '',
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
    # Backfill identity from exams when exam_id is set.
    has_exams = _table_exists(conn, "exams")
    if has_exams:
        conn.execute(
            text(
                """
                INSERT INTO exam_sessions_new (
                    id, user_id, exam_id, exam_code, exam_version,
                    mode, started_at, finished_at, score, passed
                )
                SELECT
                    s.id,
                    s.user_id,
                    s.exam_id,
                    COALESCE(e.exam_code, ''),
                    COALESCE(e.version, ''),
                    s.mode,
                    s.started_at,
                    s.finished_at,
                    s.score,
                    s.passed
                FROM exam_sessions AS s
                LEFT JOIN exams AS e ON e.id = s.exam_id
                """
            )
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO exam_sessions_new (
                    id, user_id, exam_id, exam_code, exam_version,
                    mode, started_at, finished_at, score, passed
                )
                SELECT
                    id, user_id, exam_id, '', '',
                    mode, started_at, finished_at, score, passed
                FROM exam_sessions
                """
            )
        )
    conn.execute(text("DROP TABLE exam_sessions"))
    conn.execute(text("ALTER TABLE exam_sessions_new RENAME TO exam_sessions"))
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_exam_sessions_exam_code "
            "ON exam_sessions (exam_code)"
        )
    )
    conn.execute(text("PRAGMA foreign_keys=ON"))


def _rebuild_user_answers(conn: Connection) -> None:
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        text(
            """
            CREATE TABLE user_answers_new (
                id INTEGER NOT NULL PRIMARY KEY,
                session_id INTEGER NOT NULL,
                question_id INTEGER,
                bank_question_id VARCHAR(80),
                answer_json TEXT NOT NULL,
                is_correct BOOLEAN,
                time_spent_seconds INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES exam_sessions (id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO user_answers_new (
                id, session_id, question_id, bank_question_id,
                answer_json, is_correct, time_spent_seconds
            )
            SELECT
                id, session_id, question_id, NULL,
                answer_json, is_correct, time_spent_seconds
            FROM user_answers
            """
        )
    )
    conn.execute(text("DROP TABLE user_answers"))
    conn.execute(text("ALTER TABLE user_answers_new RENAME TO user_answers"))
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_user_answers_bank_question_id "
            "ON user_answers (bank_question_id)"
        )
    )
    conn.execute(text("PRAGMA foreign_keys=ON"))


_MIGRATIONS: list[tuple[int, Callable[[Connection], None]]] = [
    (1, _migrate_v1_exam_identity),
]
