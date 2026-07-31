"""Stats page — exam/lab history, domain accuracy, recent misses."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class StatsPage(QWidget):
    title = "Stats"

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        header = QLabel("Statistics")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        try:
            from openboson import stats_service as svc

            ex = svc.exam_summary()
            lh = svc.lab_history(limit=10)
            eh = svc.exam_history(limit=10)
            lab_sum = svc.lab_summary()
            domains = svc.domain_totals()
            weak = svc.weak_domains(limit=5)
            missed = svc.recent_missed_question_ids(limit=12)
            trend = svc.score_trend(limit=10)
        except Exception as exc:
            err = QLabel(f"Could not load stats: {exc}")
            err.setProperty("role", "muted")
            self._layout.addWidget(err)
            self._layout.addStretch()
            return

        # --- Summary cards ---
        cards = QHBoxLayout()
        cards.addWidget(
            self._stat_card(
                "Exams Taken",
                str(ex["total_exams"]),
                f"{ex['passed']} passed • {ex['total_exams'] - ex['passed']} failed",
            )
        )
        cards.addWidget(
            self._stat_card(
                "Avg Exam Score",
                f"{ex['avg_score'] * 100:.0f}%",
                "across all attempts",
            )
        )
        cards.addWidget(
            self._stat_card(
                "Labs Completed",
                str(lab_sum["total_labs"]),
                f"avg {lab_sum['avg_score'] * 100:.0f}%",
            )
        )
        self._layout.addLayout(cards)

        # --- Score trend ---
        self._layout.addWidget(self._section_label("Score Trend"))
        if not trend:
            self._layout.addWidget(self._muted("No exam scores yet."))
        else:
            parts = [f"{int(p.score * 100)}%" for p in trend]
            self._layout.addWidget(self._muted(" → ".join(parts)))

        # --- Domain accuracy / weak domains ---
        self._layout.addWidget(self._section_label("Domain Accuracy"))
        show = weak if weak else domains
        if not show:
            self._layout.addWidget(self._muted("No graded answers with topic codes yet."))
        else:
            # Prefer showing all domains when few; otherwise highlight weakest.
            rows = domains if len(domains) <= 8 else weak
            for item in rows:
                self._layout.addWidget(
                    self._domain_row(item.domain_prefix, item.percent, item.total_questions)
                )

        # --- Recent misses ---
        self._layout.addWidget(self._section_label("Recent Misses"))
        if not missed:
            self._layout.addWidget(self._muted("No missed questions yet."))
        else:
            self._layout.addWidget(self._muted(", ".join(missed)))

        # --- Recent exams ---
        self._layout.addWidget(self._section_label("Recent Exams"))
        if not eh:
            self._layout.addWidget(self._muted("No exams taken yet."))
        else:
            for item in eh:
                self._layout.addWidget(
                    self._history_row(
                        f"{item.exam_code} • {item.mode}",
                        item.score,
                        item.passed,
                        item.finished_at,
                    )
                )

        # --- Recent labs ---
        self._layout.addWidget(self._section_label("Recent Labs"))
        if not lh:
            self._layout.addWidget(self._muted("No labs completed yet."))
        else:
            for item in lh:
                self._layout.addWidget(
                    self._history_row(
                        item.lab_id,
                        item.score,
                        item.score >= 0.7,
                        item.finished_at,
                    )
                )

        self._layout.addStretch()

    def _stat_card(self, label: str, value: str, sub: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(4)
        l = QLabel(label)
        l.setProperty("role", "muted")
        v.addWidget(l)
        big = QLabel(value)
        big.setStyleSheet("font-size: 28px; font-weight: 700; color: #58a6ff;")
        v.addWidget(big)
        s = QLabel(sub)
        s.setProperty("role", "muted")
        v.addWidget(s)
        return card

    def _section_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setProperty("role", "h2")
        return l

    def _muted(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setProperty("role", "muted")
        l.setWordWrap(True)
        return l

    def _domain_row(self, prefix: str, percent: float, total: int) -> QFrame:
        row = QFrame()
        row.setObjectName("Card")
        h = QHBoxLayout(row)
        h.setContentsMargins(14, 10, 14, 10)
        name = QLabel(f"Domain {prefix.rstrip('.')}")
        name.setFixedWidth(120)
        h.addWidget(name)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(percent * 100))
        h.addWidget(bar, 1)
        pct = QLabel(f"{int(percent * 100)}%")
        pct.setFixedWidth(50)
        h.addWidget(pct)
        count = QLabel(f"{total} Q")
        count.setProperty("role", "muted")
        count.setFixedWidth(50)
        h.addWidget(count)
        return row

    def _history_row(self, title: str, score: float, passed: bool, when) -> QFrame:
        row = QFrame()
        row.setObjectName("Card")
        h = QHBoxLayout(row)
        h.setContentsMargins(14, 10, 14, 10)
        mark = "✓" if passed else "✗"
        mark_lbl = QLabel(mark)
        mark_lbl.setStyleSheet("color: #3fb950;" if passed else "color: #f85149;")
        mark_lbl.setFixedWidth(24)
        h.addWidget(mark_lbl)
        name = QLabel(title)
        name.setFixedWidth(260)
        h.addWidget(name)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(score * 100))
        h.addWidget(bar, 1)
        pct = QLabel(f"{int(score * 100)}%")
        pct.setFixedWidth(50)
        h.addWidget(pct)
        ts = QLabel(when.strftime("%Y-%m-%d %H:%M") if when else "—")
        ts.setProperty("role", "muted")
        ts.setFixedWidth(130)
        h.addWidget(ts)
        return row
