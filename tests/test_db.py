"""Tests for SQLite persistence layer."""

from openboson.db import init_db
from openboson.models import Exam, ExamSession, Question, User


def _engine():
    # In-memory SQLite, shared across connection via StaticPool not needed because
    # all calls go through the same engine instance.
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", future=True)
    return engine


def test_init_db_creates_tables(tmp_path):
    from openboson.db import init_db_at

    db_file = tmp_path / "test.db"
    engine = init_db_at(db_file)
    # File should exist after init
    assert db_file.is_file()
    # Inserting a user works
    from openboson.db import get_sessionmaker

    Session = get_sessionmaker(engine)
    with Session() as s:
        u = User(display_name="test")
        s.add(u)
        s.commit()
        assert u.id is not None


def test_user_exam_session_relationships():
    engine = init_db(_engine())
    from openboson.db import get_sessionmaker

    Session = get_sessionmaker(engine)
    with Session() as s:
        u = User(display_name="alice")
        exam = Exam(title="CCNA Demo", exam_code="200-301", version="v1.1")
        s.add_all([u, exam])
        s.commit()

        sess = ExamSession(user_id=u.id, exam_id=exam.id, mode="study")
        s.add(sess)
        s.commit()

        # Reload from DB
        s.refresh(u)
        assert len(u.exam_sessions) == 1
        assert u.exam_sessions[0].exam.exam_code == "200-301"


def test_question_belongs_to_exam():
    engine = init_db(_engine())
    from openboson.db import get_sessionmaker

    Session = get_sessionmaker(engine)
    with Session() as s:
        exam = Exam(title="CCNA", exam_code="200-301")
        q = Question(
            exam=exam,
            topic_code="1.1",
            type="single_choice",
            stem_json='{"text":"What is a router?"}',
            choices_json='[{"id":"a","text":"A device"},{"id":"b","text":"A toaster"}]',
            correct_answer_json='{"answer":"a"}',
            explanation="A router forwards packets between networks.",
        )
        s.add(q)
        s.commit()

        # Reload
        s.refresh(exam)
        assert len(exam.questions) == 1
        assert exam.questions[0].topic_code == "1.1"


def test_exam_session_finished_defaults():
    engine = init_db(_engine())
    from openboson.db import get_sessionmaker

    Session = get_sessionmaker(engine)
    with Session() as s:
        u = User()
        exam = Exam(title="x", exam_code="x")
        s.add_all([u, exam])
        s.commit()
        sess = ExamSession(user_id=u.id, exam_id=exam.id)
        s.add(sess)
        s.commit()

        assert sess.finished_at is None
        assert sess.score is None
        assert sess.passed is None
        assert sess.started_at is not None
        # started_at is timezone-aware
        assert sess.started_at.tzinfo is not None
