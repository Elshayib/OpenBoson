"""Stats page — exam/lab history, domain accuracy, heatmap, recent misses."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from openboson.gui.widgets.scroll_host import ScrollHost


def _heat_color(percent: float) -> str:
    """Return a CSS background for accuracy 0..1 (red → yellow → green)."""
    p = max(0.0, min(1.0, percent))
    if p < 0.5:
        # red → yellow
        t = p / 0.5
        r, g, b = 248, int(81 + (185 - 81) * t), int(73 + (15 - 73) * t)
    else:
        t = (p - 0.5) / 0.5
        r, g, b = int(248 + (35 - 248) * t), int(185 + (134 - 185) * t), int(15 + (80 - 15) * t)
    return f"background: rgb({r},{g},{b}); color: #0d1117; border-radius: 4px;"


class StatsPage(QWidget):
    title = "Stats"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._scroll = ScrollHost(margins=(24, 24, 24, 24), spacing=16)
        root.addWidget(self._scroll, 1)
        self._layout = self._scroll.content_layout
        self._cert_filter = "all"
        self._version_filter = "all"

    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self._scroll.clear_content()

        header = QLabel("Statistics")
        header.setProperty("role", "h1")
        self._layout.addWidget(header)

        try:
            from openboson import stats_service as svc

            ex = svc.exam_summary()
            lh = svc.lab_history(limit=10)
            eh = svc.exam_history(limit=10)
            lab_sum = svc.lab_summary()
            cert = None if self._cert_filter == "all" else self._cert_filter
            version = None if self._version_filter == "all" else self._version_filter
            domains = svc.domain_totals(cert=cert)
            weak = svc.weak_domains(cert=cert, limit=5)
            missed = svc.recent_missed_question_ids(limit=12)
            trend = svc.score_trend(limit=10)
            heat_cells = svc.domain_accuracy_by_version(cert=cert, exam_version=version)
            versions = svc.list_exam_versions(cert=cert)
            domain_series = svc.domain_trend(limit=8, cert=cert)
        except Exception as exc:
            err = QLabel(f"Could not load stats: {exc}")
            err.setProperty("role", "muted")
            self._layout.addWidget(err)
            self._layout.addStretch()
            return

        # --- Filters ---
        filt = QHBoxLayout()
        cert_box = QComboBox()
        cert_box.addItem("All certs", "all")
        cert_box.addItem("CCNA", "ccna")
        cert_box.addItem("CCNP", "ccnp")
        idx = max(0, cert_box.findData(self._cert_filter))
        cert_box.setCurrentIndex(idx)
        cert_box.currentIndexChanged.connect(self._on_cert_changed)
        filt.addWidget(QLabel("Cert"))
        filt.addWidget(cert_box)
        ver_box = QComboBox()
        ver_box.addItem("All versions", "all")
        for v in versions:
            ver_box.addItem(v, v)
        vidx = max(0, ver_box.findData(self._version_filter))
        ver_box.setCurrentIndex(vidx)
        ver_box.currentIndexChanged.connect(self._on_version_changed)
        filt.addWidget(QLabel("Exam version"))
        filt.addWidget(ver_box)
        filt.addStretch()
        self._layout.addLayout(filt)
        self._cert_box = cert_box
        self._ver_box = ver_box

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

        # --- Domain × version heatmap ---
        self._layout.addWidget(self._section_label("Domain × Version Heatmap"))
        if not heat_cells:
            self._layout.addWidget(self._muted("No graded answers yet."))
        else:
            self._layout.addWidget(self._heatmap(heat_cells))

        # --- Domain trend (text) ---
        if domain_series:
            self._layout.addWidget(self._section_label("Domain Trend (recent exams)"))
            lines = []
            for pt in domain_series:
                parts = [
                    f"{prefix.rstrip('.')}:{int(pct * 100)}%"
                    for prefix, pct in sorted(pt.domains.items())
                ]
                label = pt.finished_at.strftime("%m-%d") if pt.finished_at else "?"
                lines.append(f"{label} {pt.exam_version or pt.exam_code}: " + ", ".join(parts))
            self._layout.addWidget(self._muted("\n".join(lines)))

        # --- Domain accuracy / weak domains ---
        self._layout.addWidget(self._section_label("Domain Accuracy"))
        show = weak if weak else domains
        if not show:
            self._layout.addWidget(self._muted("No graded answers with topic codes yet."))
        else:
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

    def _on_cert_changed(self, _index: int = 0) -> None:
        box = getattr(self, "_cert_box", None)
        if box is None:
            return
        self._cert_filter = box.currentData() or "all"
        self._version_filter = "all"
        self._rebuild()

    def _on_version_changed(self, _index: int = 0) -> None:
        box = getattr(self, "_ver_box", None)
        if box is None:
            return
        self._version_filter = box.currentData() or "all"
        self._rebuild()

    def _heatmap(self, cells) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        grid = QGridLayout(frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(4)
        domains = sorted({c.domain_prefix for c in cells})
        versions = sorted({c.exam_version for c in cells})
        lookup = {(c.domain_prefix, c.exam_version): c for c in cells}
        grid.addWidget(QLabel(""), 0, 0)
        for col, ver in enumerate(versions, start=1):
            lbl = QLabel(ver)
            lbl.setProperty("role", "muted")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, col)
        for row, dom in enumerate(domains, start=1):
            name = QLabel(f"D{dom.rstrip('.')}")
            name.setProperty("role", "muted")
            grid.addWidget(name, row, 0)
            for col, ver in enumerate(versions, start=1):
                cell = lookup.get((dom, ver))
                if cell is None:
                    lbl = QLabel("—")
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    pct = int(cell.percent * 100)
                    lbl = QLabel(f"{pct}%")
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet(_heat_color(cell.percent))
                    lbl.setToolTip(f"{cell.correct}/{cell.total} correct")
                lbl.setMinimumWidth(48)
                lbl.setMinimumHeight(28)
                grid.addWidget(lbl, row, col)
        return frame

    def _stat_card(self, label: str, value: str, sub: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(4)
        title = QLabel(label)
        title.setProperty("role", "muted")
        v.addWidget(title)
        big = QLabel(value)
        big.setProperty("role", "accent")
        v.addWidget(big)
        s = QLabel(sub)
        s.setProperty("role", "muted")
        s.setWordWrap(True)
        v.addWidget(s)
        return card

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "h2")
        return label

    def _muted(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "muted")
        label.setWordWrap(True)
        return label

    def _domain_row(self, prefix: str, percent: float, total: int) -> QFrame:
        row = QFrame()
        row.setObjectName("Card")
        h = QHBoxLayout(row)
        h.setContentsMargins(14, 10, 14, 10)
        name = QLabel(f"Domain {prefix.rstrip('.')}")
        name.setMinimumWidth(80)
        name.setWordWrap(True)
        h.addWidget(name, 1)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(percent * 100))
        h.addWidget(bar, 2)
        pct = QLabel(f"{int(percent * 100)}%")
        pct.setMinimumWidth(40)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(pct)
        count = QLabel(f"{total} Q")
        count.setProperty("role", "muted")
        count.setMinimumWidth(36)
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
        mark_lbl.setMinimumWidth(20)
        h.addWidget(mark_lbl)
        name = QLabel(title)
        name.setWordWrap(True)
        name.setMinimumWidth(80)
        h.addWidget(name, 2)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(score * 100))
        h.addWidget(bar, 2)
        pct = QLabel(f"{int(score * 100)}%")
        pct.setMinimumWidth(40)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(pct)
        ts = QLabel(when.strftime("%Y-%m-%d %H:%M") if when else "—")
        ts.setProperty("role", "muted")
        ts.setMinimumWidth(90)
        h.addWidget(ts)
        return row
