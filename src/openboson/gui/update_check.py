"""Background update-check worker for the GUI (keeps the UI thread free)."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from openboson.updater import (
    CheckResult,
    DownloadResult,
    UpdateInfo,
    check_for_updates,
    download_update,
)


class UpdateCheckWorker(QObject):
    finished = Signal(object)  # CheckResult

    def __init__(self, *, force: bool = False) -> None:
        super().__init__()
        self._force = force

    @Slot()
    def run(self) -> None:
        try:
            result = check_for_updates(force=self._force)
        except Exception as exc:  # noqa: BLE001 — surface as CheckResult-compatible message
            from openboson.updater import CheckStatus, ErrorKind

            result = CheckResult(
                status=CheckStatus.ERROR,
                message=f"Unexpected updater error: {exc}",
                error_kind=ErrorKind.OTHER,
            )
        self.finished.emit(result)


class UpdateDownloadWorker(QObject):
    finished = Signal(object)  # DownloadResult

    def __init__(self, info: UpdateInfo) -> None:
        super().__init__()
        self._info = info

    @Slot()
    def run(self) -> None:
        try:
            result = download_update(self._info)
        except Exception as exc:  # noqa: BLE001
            from openboson.updater import ErrorKind

            result = DownloadResult(
                ok=False,
                message=f"Unexpected download error: {exc}",
                error_kind=ErrorKind.OTHER,
            )
        self.finished.emit(result)


def start_check_thread(*, force: bool, on_finished) -> tuple[QThread, UpdateCheckWorker]:
    """Spawn a worker thread; caller must keep references until finished."""
    thread = QThread()
    worker = UpdateCheckWorker(force=force)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread, worker


def start_download_thread(info: UpdateInfo, on_finished) -> tuple[QThread, UpdateDownloadWorker]:
    thread = QThread()
    worker = UpdateDownloadWorker(info)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread, worker
