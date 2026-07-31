"""Professional topology canvas — icons, pan/zoom, click-to-select device."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from openboson.netsim.lab_schema import DeviceType, Topology


class TopologyCanvas(QWidget):
    """Interactive topology view.

    - Mouse drag empty space → pan
    - Wheel → zoom
    - Click device → ``deviceSelected(name)``
    - Professional painted icons (router / switch / pc / ap / firewall)
    """

    deviceSelected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._topology: Topology | None = None
        self._positions: dict[str, QPointF] = {}
        self._selected: str | None = None
        self._status: dict[str, str] = {}  # device -> short status
        self._tooltips: dict[str, str] = {}
        self._link_up: dict[tuple[str, str], bool] = {}  # (a,b) endpoints
        self._scale = 1.0
        self._offset = QPointF(0, 0)
        self._drag_origin: QPointF | None = None
        self._pan_origin = QPointF(0, 0)
        self._hover: str | None = None
        self.setMinimumSize(200, 160)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setStyleSheet("background-color: #0a0e16; border-radius: 8px;")

    def set_topology(self, topology: Topology) -> None:
        self._topology = topology
        self._layout_devices()
        self._selected = None
        self._scale = 1.0
        self._offset = QPointF(0, 0)
        self._link_up.clear()
        self.update()

    def set_selected(self, name: str | None) -> None:
        self._selected = name
        self.update()

    def set_device_status(self, name: str, status: str) -> None:
        self._status[name] = status
        self.update()

    def set_device_tooltip(self, name: str, text: str) -> None:
        self._tooltips[name] = text

    def set_link_states(self, states: list[dict]) -> None:
        self._link_up.clear()
        for st in states:
            a, b = st.get("a", ""), st.get("b", "")
            self._link_up[(a, b)] = bool(st.get("up"))
            self._link_up[(b, a)] = bool(st.get("up"))
        self.update()

    def _layout_devices(self) -> None:
        self._positions.clear()
        if not self._topology or not self._topology.devices:
            return
        devices = self._topology.devices
        n = len(devices)
        # Prefer role-aware layout for branch office: PCs left, SW center, R right
        {d.name: d for d in devices}
        names = [d.name for d in devices]
        if n == 4 and {"R1", "SW1", "PC1", "PC2"} <= set(names):
            self._positions["PC1"] = QPointF(70, 80)
            self._positions["PC2"] = QPointF(70, 220)
            self._positions["SW1"] = QPointF(200, 150)
            self._positions["R1"] = QPointF(340, 150)
            return
        cx, cy, rx, ry = 200.0, 150.0, 140.0, 100.0
        if n == 1:
            self._positions[devices[0].name] = QPointF(cx, cy)
            return
        if n == 2:
            self._positions[devices[0].name] = QPointF(cx - 90, cy)
            self._positions[devices[1].name] = QPointF(cx + 90, cy)
            return
        for i, d in enumerate(devices):
            ang = (2 * math.pi * i / n) - math.pi / 2
            self._positions[d.name] = QPointF(cx + rx * math.cos(ang), cy + ry * math.sin(ang))

    def _device_type(self, name: str) -> DeviceType:
        if not self._topology:
            return DeviceType.ROUTER
        for d in self._topology.devices:
            if d.name == name:
                return d.type
        return DeviceType.ROUTER

    def _map(self, p: QPointF) -> QPointF:
        return QPointF(
            p.x() * self._scale + self._offset.x() + self.width() * 0.5 - 200 * self._scale,
            p.y() * self._scale + self._offset.y() + self.height() * 0.5 - 150 * self._scale,
        )

    def _imap(self, p: QPointF) -> QPointF:
        return QPointF(
            (p.x() - self._offset.x() - self.width() * 0.5 + 200 * self._scale) / self._scale,
            (p.y() - self._offset.y() - self.height() * 0.5 + 150 * self._scale) / self._scale,
        )

    def _hit(self, pos: QPointF) -> str | None:
        logical = self._imap(pos)
        for name, p in self._positions.items():
            if (logical - p).manhattanLength() < 36:
                return name
        return None

    # -----/ Events /-----
    def wheelEvent(self, e: QWheelEvent) -> None:  # noqa: N802
        delta = e.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self._scale = max(0.4, min(2.5, self._scale * factor))
        self.update()

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            name = self._hit(e.position())
            if name:
                self._selected = name
                self.deviceSelected.emit(name)
                self.update()
            else:
                self._drag_origin = e.position()
                self._pan_origin = QPointF(self._offset)

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._drag_origin is not None:
            delta = e.position() - self._drag_origin
            self._offset = self._pan_origin + delta
            self.update()
            return
        hover = self._hit(e.position())
        if hover != self._hover:
            self._hover = hover
            self.setCursor(
                Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor
            )
            if hover and hover in self._tooltips:
                self.setToolTip(self._tooltips[hover])
            else:
                self.setToolTip("")
            self.update()
        return

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._drag_origin = None

    # -----/ Paint /-----
    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background grid
        p.fillRect(self.rect(), QColor("#0a0e16"))
        grid = QPen(QColor(30, 40, 60, 80), 1)
        p.setPen(grid)
        step = int(24 * self._scale)
        if step >= 8:
            for x in range(0, self.width(), step):
                p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), step):
                p.drawLine(0, y, self.width(), y)

        if not self._topology:
            p.setPen(QColor("#6e7681"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No topology loaded")
            return

        # Links
        for link in self._topology.links:
            a_dev = link.a.split("/")[0]
            b_dev = link.b.split("/")[0]
            if a_dev not in self._positions or b_dev not in self._positions:
                continue
            a = self._map(self._positions[a_dev])
            b = self._map(self._positions[b_dev])
            up = self._link_up.get((link.a, link.b), False)
            color = QColor("#3fb950") if up else QColor("#3d5a80")
            pen = QPen(color, max(2, int((3 if up else 2) * self._scale)))
            p.setPen(pen)
            p.drawLine(a, b)
            # Port LED near each end
            led = QColor("#3fb950") if up else QColor("#6e7681")
            p.setBrush(led)
            p.setPen(Qt.PenStyle.NoPen)

            # Points 18px from device centers along the cable
            def _near(src: QPointF, dst: QPointF) -> QPointF:
                dx, dy = dst.x() - src.x(), dst.y() - src.y()
                length = max((dx * dx + dy * dy) ** 0.5, 1.0)
                t = 28 * self._scale / length
                return QPointF(src.x() + dx * t, src.y() + dy * t)

            p.drawEllipse(_near(a, b), 4 * self._scale, 4 * self._scale)
            p.drawEllipse(_near(b, a), 4 * self._scale, 4 * self._scale)
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            a_if = link.a.split("/", 1)[-1].replace("GigabitEthernet", "Gi")
            b_if = link.b.split("/", 1)[-1].replace("GigabitEthernet", "Gi")
            p.setPen(QColor("#8b9cb3"))
            font = QFont("Segoe UI", max(7, int(8 * self._scale)))
            p.setFont(font)
            p.drawText(mid + QPointF(-40, -6), f"{a_if}")
            p.drawText(mid + QPointF(-40, 10), f"{b_if}")

        # Devices
        for name, pos in self._positions.items():
            self._draw_device(p, name, self._map(pos), self._device_type(name))

        # Legend / hint
        p.setPen(QColor("#6e7681"))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(
            10,
            self.height() - 10,
            "Click device → console   ·   Drag background → pan   ·   Wheel → zoom",
        )

    def _draw_device(self, p: QPainter, name: str, center: QPointF, dtype: DeviceType) -> None:
        selected = name == self._selected
        hover = name == self._hover
        s = 28 * self._scale

        # Glow when selected
        if selected or hover:
            glow = QColor("#58a6ff" if selected else "#388bfd")
            glow.setAlpha(55 if selected else 30)
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(center, s + 14, s + 14)

        if dtype == DeviceType.ROUTER:
            self._icon_router(p, center, s, selected)
        elif dtype == DeviceType.SWITCH:
            self._icon_switch(p, center, s, selected)
        elif dtype == DeviceType.PC:
            self._icon_pc(p, center, s, selected)
        elif dtype == DeviceType.FIREWALL:
            self._icon_firewall(p, center, s, selected)
        else:
            self._icon_ap(p, center, s, selected)

        # Label
        p.setPen(QColor("#e6edf3") if selected else QColor("#c9d1d9"))
        font = QFont("Segoe UI Semibold", max(9, int(10 * self._scale)))
        p.setFont(font)
        label = name
        st = self._status.get(name)
        metrics_y = center.y() + s + 4
        p.drawText(
            QRectF(center.x() - 60, metrics_y, 120, 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            label,
        )
        if st:
            p.setPen(QColor("#7ee787"))
            p.setFont(QFont("Segoe UI", max(7, int(8 * self._scale))))
            p.drawText(
                QRectF(center.x() - 70, metrics_y + 14, 140, 14),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                st,
            )

    def _icon_router(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        # Cylinder-like router body
        body = QColor("#1f6feb") if selected else QColor("#1954b8")
        p.setBrush(body)
        p.setPen(QPen(QColor("#79c0ff"), 1.5))
        rect = QRectF(c.x() - s, c.y() - s * 0.55, s * 2, s * 1.1)
        p.drawRoundedRect(rect, 8, 8)
        # Top ellipse hint
        p.setBrush(QColor("#388bfd"))
        p.drawEllipse(QRectF(c.x() - s * 0.7, c.y() - s * 0.75, s * 1.4, s * 0.45))
        # Antenna
        p.setPen(QPen(QColor("#79c0ff"), 2))
        p.drawLine(QPointF(c.x(), c.y() - s * 0.7), QPointF(c.x(), c.y() - s * 1.15))
        p.drawEllipse(QPointF(c.x(), c.y() - s * 1.2), 3, 3)
        # Port dots
        p.setBrush(QColor("#7ee787"))
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(4):
            p.drawEllipse(QPointF(c.x() - s * 0.55 + i * s * 0.35, c.y() + s * 0.25), 2.5, 2.5)

    def _icon_switch(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#238636") if selected else QColor("#1a7f37")
        p.setBrush(body)
        p.setPen(QPen(QColor("#3fb950"), 1.5))
        rect = QRectF(c.x() - s * 1.15, c.y() - s * 0.45, s * 2.3, s * 0.95)
        p.drawRoundedRect(rect, 6, 6)
        # Port row
        p.setBrush(QColor("#0d1117"))
        for i in range(6):
            pr = QRectF(c.x() - s * 0.95 + i * s * 0.32, c.y() - s * 0.12, s * 0.22, s * 0.28)
            p.drawRect(pr)
        # LED
        p.setBrush(QColor("#7ee787"))
        p.drawEllipse(QPointF(c.x() + s * 0.95, c.y() - s * 0.25), 3, 3)

    def _icon_pc(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#6e40c9") if selected else QColor("#5a32a3")
        p.setBrush(body)
        p.setPen(QPen(QColor("#d2a8ff"), 1.5))
        # Monitor
        mon = QRectF(c.x() - s * 0.85, c.y() - s * 0.7, s * 1.7, s * 1.15)
        p.drawRoundedRect(mon, 4, 4)
        p.setBrush(QColor("#0d1117"))
        p.drawRect(QRectF(c.x() - s * 0.7, c.y() - s * 0.55, s * 1.4, s * 0.85))
        # Stand
        p.setBrush(body)
        p.drawRect(QRectF(c.x() - s * 0.12, c.y() + s * 0.45, s * 0.24, s * 0.25))
        p.drawRect(QRectF(c.x() - s * 0.4, c.y() + s * 0.7, s * 0.8, s * 0.12))

    def _icon_firewall(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#da3633") if selected else QColor("#a40e26")
        p.setBrush(body)
        p.setPen(QPen(QColor("#ff7b72"), 1.5))
        path = QPainterPath()
        path.moveTo(c.x(), c.y() - s)
        path.lineTo(c.x() + s, c.y() - s * 0.3)
        path.lineTo(c.x() + s * 0.75, c.y() + s)
        path.lineTo(c.x() - s * 0.75, c.y() + s)
        path.lineTo(c.x() - s, c.y() - s * 0.3)
        path.closeSubpath()
        p.drawPath(path)

    def _icon_ap(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#bf8700") if selected else QColor("#9e6a03")
        p.setBrush(body)
        p.setPen(QPen(QColor("#d4a72c"), 1.5))
        p.drawEllipse(c, s * 0.7, s * 0.7)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#e3b341"), 1.5))
        p.drawArc(QRectF(c.x() - s, c.y() - s, s * 2, s * 2), 30 * 16, 120 * 16)
        p.drawArc(QRectF(c.x() - s * 1.3, c.y() - s * 1.3, s * 2.6, s * 2.6), 30 * 16, 120 * 16)
