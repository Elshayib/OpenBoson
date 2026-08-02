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
    - Wheel → zoom toward cursor
    - Click device → ``deviceSelected(name)``
    - Honors ``Device.x`` / ``Device.y`` when set
    """

    deviceSelected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopologyCanvas")
        self._topology: Topology | None = None
        self._positions: dict[str, QPointF] = {}
        self._selected: str | None = None
        self._status: dict[str, str] = {}
        self._tooltips: dict[str, str] = {}
        self._link_up: dict[tuple[str, str], bool] = {}
        self._scale = 1.0
        self._offset = QPointF(0, 0)
        self._drag_origin: QPointF | None = None
        self._pan_origin = QPointF(0, 0)
        self._hover: str | None = None
        self.setMinimumSize(200, 160)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def _is_light(self) -> bool:
        return self.palette().window().color().lightness() > 140

    def _bg(self) -> QColor:
        return QColor("#f6f8fa") if self._is_light() else QColor("#0a0e16")

    def _grid(self) -> QColor:
        return QColor(210, 215, 220, 90) if self._is_light() else QColor(30, 40, 60, 80)

    def _muted(self) -> QColor:
        return QColor("#656d76") if self._is_light() else QColor("#6e7681")

    def _label(self) -> QColor:
        return QColor("#1f2328") if self._is_light() else QColor("#e6edf3")

    def set_topology(self, topology: Topology) -> None:
        self._topology = topology
        self._layout_devices()
        self._selected = None
        self._scale = 1.0
        self._offset = QPointF(0, 0)
        self._link_up.clear()
        self._fit_view()
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
        # Prefer author layout when any device carries coordinates.
        if any(d.x is not None and d.y is not None for d in devices):
            for d in devices:
                if d.x is not None and d.y is not None:
                    self._positions[d.name] = QPointF(float(d.x), float(d.y))
                else:
                    self._positions[d.name] = QPointF(200.0, 150.0)
            return

        n = len(devices)
        names = [d.name for d in devices]
        if n == 4 and {"R1", "SW1", "PC1", "PC2"} <= set(names):
            self._positions["PC1"] = QPointF(70, 80)
            self._positions["PC2"] = QPointF(70, 220)
            self._positions["SW1"] = QPointF(200, 150)
            self._positions["R1"] = QPointF(340, 150)
            return

        # Role bands: PCs left, switches center, routers/firewall right.
        bands: dict[str, list] = {"pc": [], "switch": [], "router": [], "other": []}
        for d in devices:
            if d.type == DeviceType.PC:
                bands["pc"].append(d)
            elif d.type == DeviceType.SWITCH:
                bands["switch"].append(d)
            elif d.type in (DeviceType.ROUTER, DeviceType.FIREWALL):
                bands["router"].append(d)
            else:
                bands["other"].append(d)
        if sum(1 for v in bands.values() if v) >= 2 and n >= 3:
            cols = [
                ("pc", 80.0),
                ("switch", 220.0),
                ("router", 360.0),
                ("other", 280.0),
            ]
            for key, x in cols:
                group = bands[key]
                if not group:
                    continue
                for i, d in enumerate(group):
                    y = 80.0 + i * (200.0 / max(len(group), 1))
                    self._positions[d.name] = QPointF(x, y)
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

    def _fit_view(self) -> None:
        if not self._positions or self.width() < 40 or self.height() < 40:
            return
        xs = [p.x() for p in self._positions.values()]
        ys = [p.y() for p in self._positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        pad = 80.0
        w = max(max_x - min_x, 80.0) + pad
        h = max(max_y - min_y, 80.0) + pad
        sx = (self.width() * 0.85) / w
        sy = (self.height() * 0.85) / h
        self._scale = max(0.5, min(1.8, min(sx, sy)))
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        # _map centers around logical (200, 150); offset so content center hits widget center.
        self._offset = QPointF(
            (200 - cx) * self._scale,
            (150 - cy) * self._scale,
        )

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

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._topology and self._positions:
            self._fit_view()

    def wheelEvent(self, e: QWheelEvent) -> None:  # noqa: N802
        delta = e.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        old = self._scale
        new = max(0.4, min(2.5, old * factor))
        if new == old:
            return
        # Zoom toward cursor: keep the logical point under the cursor stable.
        mouse = e.position()
        before = self._imap(mouse)
        self._scale = new
        after_screen = self._map(before)
        self._offset += mouse - after_screen
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

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._drag_origin = None

    def mouseDoubleClickEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton and self._hit(e.position()) is None:
            self._fit_view()
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), self._bg())
        grid = QPen(self._grid(), 1)
        p.setPen(grid)
        step = int(24 * self._scale)
        if step >= 8:
            for x in range(0, self.width(), step):
                p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), step):
                p.drawLine(0, y, self.width(), y)

        if not self._topology:
            p.setPen(self._muted())
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No topology loaded")
            return

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
            led = QColor("#3fb950") if up else QColor("#6e7681")
            p.setBrush(led)
            p.setPen(Qt.PenStyle.NoPen)

            def _near(src: QPointF, dst: QPointF) -> QPointF:
                dx, dy = dst.x() - src.x(), dst.y() - src.y()
                length = max((dx * dx + dy * dy) ** 0.5, 1.0)
                t = 28 * self._scale / length
                return QPointF(src.x() + dx * t, src.y() + dy * t)

            p.drawEllipse(_near(a, b), 4 * self._scale, 4 * self._scale)
            p.drawEllipse(_near(b, a), 4 * self._scale, 4 * self._scale)
            # Single combined label near midpoint to reduce clutter.
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            a_if = link.a.split("/", 1)[-1].replace("GigabitEthernet", "Gi")
            b_if = link.b.split("/", 1)[-1].replace("GigabitEthernet", "Gi")
            p.setPen(self._muted())
            font = QFont("Segoe UI", max(7, int(8 * self._scale)))
            p.setFont(font)
            p.drawText(mid + QPointF(-36, -4), f"{a_if} — {b_if}")

        for name, pos in self._positions.items():
            self._draw_device(p, name, self._map(pos), self._device_type(name))

        p.setPen(self._muted())
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(
            10,
            self.height() - 10,
            "Click device → console   ·   Drag → pan   ·   Wheel → zoom   ·   Double-click → fit",
        )

    def _draw_device(self, p: QPainter, name: str, center: QPointF, dtype: DeviceType) -> None:
        selected = name == self._selected
        hover = name == self._hover
        s = 28 * self._scale

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

        p.setPen(self._label() if selected else self._muted())
        font = QFont("Segoe UI Semibold", max(9, int(10 * self._scale)))
        p.setFont(font)
        metrics_y = center.y() + s + 4
        p.drawText(
            QRectF(center.x() - 60, metrics_y, 120, 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            name,
        )
        st = self._status.get(name)
        if st:
            p.setPen(QColor("#1a7f37") if self._is_light() else QColor("#7ee787"))
            p.setFont(QFont("Segoe UI", max(7, int(8 * self._scale))))
            p.drawText(
                QRectF(center.x() - 70, metrics_y + 14, 140, 14),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                st,
            )

    def _icon_router(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#1f6feb") if selected else QColor("#1954b8")
        p.setBrush(body)
        p.setPen(QPen(QColor("#79c0ff"), 1.5))
        rect = QRectF(c.x() - s, c.y() - s * 0.55, s * 2, s * 1.1)
        p.drawRoundedRect(rect, 8, 8)
        p.setBrush(QColor("#388bfd"))
        p.drawEllipse(QRectF(c.x() - s * 0.7, c.y() - s * 0.75, s * 1.4, s * 0.45))
        p.setPen(QPen(QColor("#79c0ff"), 2))
        p.drawLine(QPointF(c.x(), c.y() - s * 0.7), QPointF(c.x(), c.y() - s * 1.15))
        p.drawEllipse(QPointF(c.x(), c.y() - s * 1.2), 3, 3)
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
        p.setBrush(QColor("#0d1117"))
        for i in range(6):
            pr = QRectF(c.x() - s * 0.95 + i * s * 0.32, c.y() - s * 0.12, s * 0.22, s * 0.28)
            p.drawRect(pr)
        p.setBrush(QColor("#7ee787"))
        p.drawEllipse(QPointF(c.x() + s * 0.95, c.y() - s * 0.25), 3, 3)

    def _icon_pc(self, p: QPainter, c: QPointF, s: float, selected: bool) -> None:
        body = QColor("#6e40c9") if selected else QColor("#5a32a3")
        p.setBrush(body)
        p.setPen(QPen(QColor("#d2a8ff"), 1.5))
        mon = QRectF(c.x() - s * 0.85, c.y() - s * 0.7, s * 1.7, s * 1.15)
        p.drawRoundedRect(mon, 4, 4)
        p.setBrush(QColor("#0d1117"))
        p.drawRect(QRectF(c.x() - s * 0.7, c.y() - s * 0.55, s * 1.4, s * 0.85))
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
