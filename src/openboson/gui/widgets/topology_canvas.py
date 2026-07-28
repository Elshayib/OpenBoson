"""Network topology canvas — a read-only SVG-like view of lab devices/links.

Uses QPainter to draw routers/switches as rounded rectangles with labels and
links as lines. Hover shows a device's interfaces.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from openboson.netsim.lab_schema import Topology

_DEVICE_COLORS = {
    "router": QColor("#2f81f7"),
    "switch": QColor("#3fb950"),
    "ap": QColor("#bc8cff"),
    "firewall": QColor("#f85149"),
    "pc": QColor("#8b949e"),
}


class TopologyCanvas(QWidget):
    """Renders a lab topology. Devices are laid out on a simple grid."""

    def __init__(self, topology: Topology | None = None) -> None:
        super().__init__()
        self.setMinimumHeight(220)
        self._topology = topology
        self._layout: dict[str, QPointF] = {}
        self._recompute_layout()

    def set_topology(self, topology: Topology) -> None:
        self._topology = topology
        self._recompute_layout()
        self.update()

    def _recompute_layout(self) -> None:
        self._layout.clear()
        if not self._topology:
            return
        devices = self._topology.devices
        cols = max(1, (len(devices) + 1) // 2)
        for i, dev in enumerate(devices):
            row = i // cols
            col = i % cols
            x = 60 + col * 220
            y = 50 + row * 120
            self._layout[dev.name] = QPointF(x, y)

    def paintEvent(self, event) -> None:  # noqa: ANN001 - Qt event type
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b1019"))
        if not self._topology:
            return

        # Draw links first (under devices).
        pen = QPen(QColor("#30363d"))
        pen.setWidth(2)
        painter.setPen(pen)
        for link in self._topology.links:
            a_name = link.a.split("/")[0]
            b_name = link.b.split("/")[0]
            pa = self._layout.get(a_name)
            pb = self._layout.get(b_name)
            if pa and pb:
                painter.drawLine(pa, pb)

        # Draw devices.
        for dev in self._topology.devices:
            p = self._layout.get(dev.name)
            if not p:
                continue
            color = _DEVICE_COLORS.get(dev.type.value, QColor("#8b949e"))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            rect = QRectF(p.x() - 50, p.y() - 22, 100, 44)
            painter.drawRoundedRect(rect, 8, 8)
            painter.setPen(QColor("#0b1019"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, dev.name)
