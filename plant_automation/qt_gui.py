"""Cross-platform Qt dashboard for the farm automation service."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QPointF, QProcess, QRectF, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .adb import AdbError, AndroidBridge
from .crops import CropConfigError, CropProfile, load_crops
from .device_profile import DeviceProfile, DeviceProfileError, load_device_profile
from .dependency_setup import check_dependencies, install_command, missing_summary
from .monitor import FarmSnapshot, capture_farm_snapshot
from .farm import PLOT_CENTERS


APP_STYLE = """
QMainWindow, QWidget { background: #f5f7fb; color: #1e293b; font-family: Arial; font-size: 13px; }
QGroupBox { background: white; border: 1px solid #e2e8f0; border-radius: 12px; margin-top: 12px; padding: 14px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 5px; color: #475569; }
QPushButton { background: #e8eef8; border: 0; border-radius: 8px; padding: 9px 12px; font-weight: 700; color: #334155; }
QPushButton:hover { background: #dce7f7; }
QPushButton#primary { background: #2563eb; color: white; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#danger { background: #dc2626; color: white; }
QPushButton#danger:hover { background: #b91c1c; }
QComboBox, QDoubleSpinBox { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 7px; min-height: 30px; padding: 2px 8px; }
QLabel#title { font-size: 24px; font-weight: 800; color: #0f172a; }
QLabel#subtitle, QLabel#muted { color: #64748b; }
QLabel#badge { background: #e2e8f0; border-radius: 10px; padding: 7px 10px; font-weight: 700; }
QLabel#log { background: #0f172a; color: #dbeafe; border-radius: 10px; padding: 12px; font-family: Menlo, monospace; }
"""


class SnapshotWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, serial: str, reference: Path, profile: DeviceProfile) -> None:
        super().__init__()
        self.serial = serial
        self.reference = reference
        self.profile = profile

    def run(self) -> None:
        try:
            snapshot = capture_farm_snapshot(AndroidBridge(self.serial), self.reference, self.profile)
        except (AdbError, OSError, RuntimeError) as error:
            self.failed.emit(str(error))
            return
        self.ready.emit(snapshot)


class FarmMap(QWidget):
    """Paints the calibrated 16-tile isometric layout as a compact farm map."""

    # A small padding around the calibrated screen coordinates prevents the
    # outer left/right plots from being clipped by the dashboard map.
    bounds = (350, 150, 2000, 820)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(330)
        self.occupied: set[int] | None = None

    def update_status(self, occupied: tuple[int, ...] | None) -> None:
        self.occupied = set(occupied) if occupied is not None else None
        self.update()

    def _center(self, point: tuple[int, int], area: QRectF) -> QPointF:
        x1, y1, x2, y2 = self.bounds
        return QPointF(area.left() + (point[0] - x1) * area.width() / (x2 - x1), area.top() + (point[1] - y1) * area.height() / (y2 - y1))

    @staticmethod
    def _diamond(center: QPointF, width: float, height: float) -> QPolygonF:
        return QPolygonF([
            QPointF(center.x(), center.y() - height / 2),
            QPointF(center.x() + width / 2, center.y()),
            QPointF(center.x(), center.y() + height / 2),
            QPointF(center.x() - width / 2, center.y()),
        ])

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#edf5e9"))
        area = QRectF(15, 15, self.width() - 30, self.height() - 30)
        painter.setPen(QPen(QColor("#c6dfba"), 1))
        painter.setBrush(QColor("#e3f1dd"))
        painter.drawRoundedRect(area, 16, 16)
        width = min(145.0, area.width() * 0.25)
        height = width * 0.43
        for index, point in enumerate(PLOT_CENTERS, start=1):
            center = self._center(point, area)
            tile = self._diamond(center, width, height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 23, 42, 34))
            painter.drawPolygon(QPolygonF([QPointF(vertex.x(), vertex.y() + 5) for vertex in tile]))
            if self.occupied is None:
                top, bottom, border = QColor("#d7dee8"), QColor("#b6c2d0"), QColor("#9aa9ba")
            else:
                top, bottom, border = QColor("#b9794a"), QColor("#754228"), QColor("#5e351f")
            gradient = QLinearGradient(center.x(), center.y() - height / 2, center.x(), center.y() + height / 2)
            gradient.setColorAt(0, top)
            gradient.setColorAt(1, bottom)
            painter.setBrush(gradient)
            painter.setPen(QPen(border, 1.4))
            painter.drawPolygon(tile)
            if self.occupied is not None and index in self.occupied:
                self._plant(painter, center, width, height)
            elif self.occupied is not None:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#61381f"))
                for dx, dy in ((-.15, -.02), (.11, .07), (0, -.13)):
                    painter.drawEllipse(QPointF(center.x() + width * dx, center.y() + width * dy), 2, 2)
            if self.occupied is not None:
                self._index(painter, index, center, width, height)

    @staticmethod
    def _plant(painter: QPainter, center: QPointF, width: float, height: float) -> None:
        painter.setPen(QPen(QColor("#267446"), max(3, width * .045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(center.x(), center.y() + height * .16), QPointF(center.x(), center.y() - height * .48))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4ade80"))
        painter.drawEllipse(QRectF(center.x() - width * .18, center.y() - height * .48, width * .18, height * .3))
        painter.drawEllipse(QRectF(center.x(), center.y() - height * .64, width * .18, height * .3))
        painter.setBrush(QColor("#65a30d"))
        painter.drawEllipse(QRectF(center.x() + width * .03, center.y() - height * .10, width * .12, height * .4))

    @staticmethod
    def _index(painter: QPainter, index: int, center: QPointF, width: float, height: float) -> None:
        point, radius = QPointF(center.x() - width * .28, center.y() - height * .10), max(7, width * .075)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor("#334155"))
        painter.drawEllipse(point, radius, radius)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(point.x() - radius, point.y() - radius, radius * 2, radius * 2), Qt.AlignmentFlag.AlignCenter, str(index))


class FarmDashboard(QMainWindow):
    def __init__(self, initial_serial: str | None = None, device_profile_path: Path = Path("config/device-profiles/default-farm.json")) -> None:
        super().__init__()
        self.setWindowTitle("Plant Automation")
        self.resize(1280, 820)
        self.setMinimumSize(1050, 680)
        self.setStyleSheet(APP_STYLE)
        self.reference = Path("captures/empty-reference.png")
        self.crop_config = Path("config/crops.json")
        self.device_profile_path = device_profile_path
        self.device_profile = load_device_profile(device_profile_path)
        self.crops = load_crops(self.crop_config)
        self.snapshot_worker: SnapshotWorker | None = None
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_process_output)
        self.process.readyReadStandardError.connect(self._read_process_output)
        self.process.finished.connect(self._automation_finished)
        self.setup_process = QProcess(self)
        self.setup_process.finished.connect(self._dependency_install_finished)
        self._build(initial_serial or "")
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(2500)
        self.refresh_timer.timeout.connect(self.refresh_snapshot)
        self.refresh_timer.start()
        self.refresh_devices()
        self.refresh_snapshot()
        self.refresh_dependencies()

    def _build(self, initial_serial: str) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Plant Automation")
        title.setObjectName("title")
        titles.addWidget(title)
        subtitle = QLabel("Dashboard điều khiển trồng, tưới và thu hoạch qua ADB")
        subtitle.setObjectName("subtitle")
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.connection_badge = QLabel("Đang kiểm tra thiết bị")
        self.connection_badge.setObjectName("badge")
        header.addWidget(self.connection_badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(self._controls(initial_serial))
        left.addWidget(self._farm_status())
        left.addStretch()
        body.addLayout(left, 4)

        right = QVBoxLayout()
        right.addWidget(self._preview())
        right.addWidget(self._log_panel())
        body.addLayout(right, 6)
        layout.addLayout(body, 1)

    def _controls(self, initial_serial: str) -> QGroupBox:
        group = QGroupBox("Điều khiển")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        layout.addWidget(QLabel("Thiết bị"), 0, 0)
        self.device_selector = QComboBox()
        self.device_selector.setEditable(True)
        self.device_selector.setCurrentText(initial_serial)
        layout.addWidget(self.device_selector, 0, 1)
        scan_devices = QPushButton("Quét")
        scan_devices.clicked.connect(self.refresh_devices)
        layout.addWidget(scan_devices, 0, 2)
        open_mirror = QPushButton("Mở Mirror")
        open_mirror.clicked.connect(self.open_mirror_now)
        layout.addWidget(open_mirror, 0, 3)
        self.setup_tools_button = QPushButton("Cài ADB / scrcpy")
        self.setup_tools_button.clicked.connect(self.install_dependencies)
        layout.addWidget(self.setup_tools_button, 1, 3)
        layout.addWidget(QLabel("Cây trồng"), 1, 0)
        self.crop_selector = QComboBox()
        for crop in self.crops:
            self.crop_selector.addItem(crop.name, crop)
        layout.addWidget(self.crop_selector, 1, 1, 1, 2)
        layout.addWidget(QLabel("Quét mỗi"), 2, 0)
        self.interval = QDoubleSpinBox()
        self.interval.setRange(1, 60)
        self.interval.setValue(3)
        self.interval.setSuffix(" giây")
        layout.addWidget(self.interval, 2, 1)
        layout.addWidget(QLabel("Chờ popup"), 3, 0)
        self.popup_wait = QDoubleSpinBox()
        self.popup_wait.setRange(1, 120)
        self.popup_wait.setValue(5)
        self.popup_wait.setSuffix(" giây")
        layout.addWidget(self.popup_wait, 3, 1)
        self.open_mirror = QCheckBox("Tự mở Mirror khi bắt đầu")
        self.open_mirror.setChecked(True)
        layout.addWidget(self.open_mirror, 2, 2)
        self.confirm_actions = QCheckBox("Cho phép thao tác thật")
        layout.addWidget(self.confirm_actions, 3, 2)
        self.start_button = QPushButton("▶  Bắt đầu vòng lặp")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_automation)
        layout.addWidget(self.start_button, 4, 0, 1, 2)
        self.stop_button = QPushButton("■  Dừng an toàn")
        self.stop_button.setObjectName("danger")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_automation)
        layout.addWidget(self.stop_button, 4, 2)
        note = QLabel("Bỏ chọn thao tác thật để chỉ xem trước; không có chạm nào được gửi.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note, 5, 0, 1, 3)
        return group

    def _farm_status(self) -> QGroupBox:
        group = QGroupBox("Trạng thái 16 ô đất")
        layout = QVBoxLayout(group)
        self.farm_map = FarmMap()
        layout.addWidget(self.farm_map)
        self.farm_summary = QLabel("Đang chờ ảnh quét…")
        self.farm_summary.setObjectName("muted")
        layout.addWidget(self.farm_summary)
        return group

    def _preview(self) -> QGroupBox:
        group = QGroupBox("Màn hình điện thoại")
        layout = QVBoxLayout(group)
        self.preview = QLabel("Đang chờ ảnh quét…")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(310)
        self.preview.setStyleSheet("background: #e2e8f0; border-radius: 10px; color: #64748b;")
        layout.addWidget(self.preview)
        return group

    def _log_panel(self) -> QGroupBox:
        group = QGroupBox("Nhật ký hoạt động")
        layout = QVBoxLayout(group)
        self.log = QLabel("Sẵn sàng.")
        self.log.setObjectName("log")
        self.log.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.log.setWordWrap(True)
        self.log.setMinimumHeight(145)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.log)
        layout.addWidget(scroll)
        return group

    def refresh_devices(self) -> None:
        try:
            devices = [device.serial for device in AndroidBridge.devices() if device.state == "device"]
        except AdbError as error:
            self.connection_badge.setText("Không tìm thấy ADB")
            self._append_log(f"Lỗi ADB: {error}")
            return
        current = self.device_selector.currentText()
        self.device_selector.clear()
        self.device_selector.addItems(devices)
        self.device_selector.setCurrentText(current if current else (devices[0] if devices else ""))
        self.connection_badge.setText(f"{len(devices)} thiết bị sẵn sàng" if devices else "Chưa có thiết bị")

    def refresh_dependencies(self) -> None:
        status = check_dependencies()
        if status.ready:
            self.setup_tools_button.setText("ADB / scrcpy: Sẵn sàng")
            self.setup_tools_button.setEnabled(False)
            return
        self.setup_tools_button.setText(f"Cài {missing_summary(status)}")
        self.setup_tools_button.setEnabled(install_command() is not None)

    def install_dependencies(self) -> None:
        status = check_dependencies()
        if status.ready:
            self.refresh_dependencies()
            return
        command = install_command()
        if command is None:
            QMessageBox.information(self, "Cài công cụ", "Hãy cài ADB và scrcpy theo hướng dẫn sử dụng.")
            return
        answer = QMessageBox.question(
            self,
            "Cài ADB và scrcpy",
            f"Thiếu {missing_summary(status)}. Cho phép trình quản lý gói của hệ điều hành tải và cài công cụ này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        program, arguments = command
        self.setup_tools_button.setEnabled(False)
        self.setup_tools_button.setText("Đang cài công cụ…")
        self._append_log("Đang cài ADB/scrcpy; có thể xuất hiện yêu cầu quyền hệ thống.")
        self.setup_process.start(program, arguments)

    def _dependency_install_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self.refresh_dependencies()
        if check_dependencies().ready:
            self._append_log("Đã cài ADB và scrcpy. Có thể cần quét lại thiết bị.")
            self.refresh_devices()
        else:
            self._append_log(f"Cài công cụ chưa hoàn tất (mã {exit_code}); xem lại quyền hoặc mạng.")

    def refresh_snapshot(self) -> None:
        if self.snapshot_worker and self.snapshot_worker.isRunning():
            return
        serial = self.device_selector.currentText().strip()
        if not serial or not self.reference.exists():
            return
        self.snapshot_worker = SnapshotWorker(serial, self.reference, self.device_profile)
        self.snapshot_worker.ready.connect(self._update_snapshot)
        self.snapshot_worker.failed.connect(self._snapshot_failed)
        self.snapshot_worker.finished.connect(self._snapshot_finished)
        self.snapshot_worker.finished.connect(self.snapshot_worker.deleteLater)
        self.snapshot_worker.start()

    def open_mirror_now(self) -> None:
        serial = self.device_selector.currentText().strip()
        if not serial:
            QMessageBox.warning(self, "Thiếu thiết bị", "Hãy chọn thiết bị Android trước khi mở Mirror.")
            return
        try:
            AndroidBridge(serial).mirror()
        except AdbError as error:
            QMessageBox.critical(self, "Không mở được Mirror", str(error))
            return
        self._append_log(f"Đã mở Mirror cho thiết bị {serial}.")

    def _snapshot_finished(self) -> None:
        self.snapshot_worker = None

    def _update_snapshot(self, snapshot: FarmSnapshot) -> None:
        image = QImage.fromData(snapshot.image_png, "PNG")
        pixmap = QPixmap.fromImage(image)
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        status = snapshot.status
        if status.popup_detected:
            self.connection_badge.setText("Popup che giao diện")
            self.farm_summary.setText("Đang chờ popup biến mất trước khi nhận diện ruộng.")
            self.farm_map.update_status(None)
            return
        self.farm_map.update_status(status.occupied)
        self.connection_badge.setText("Điện thoại đã kết nối")
        self.farm_summary.setText(f"{len(status.occupied)} ô có cây • {len(status.empty)} ô trống")

    def _snapshot_failed(self, error: str) -> None:
        self.connection_badge.setText("Mất kết nối hoặc lỗi quét")
        self.farm_summary.setText("Không thể cập nhật trạng thái ruộng.")
        self._append_log(f"Quét thất bại: {error}")

    def start_automation(self) -> None:
        serial = self.device_selector.currentText().strip()
        if not serial:
            QMessageBox.warning(self, "Thiếu thiết bị", "Hãy chọn thiết bị Android trước khi chạy.")
            return
        crop: CropProfile = self.crop_selector.currentData()
        worker_arguments = [
            "--serial", serial, "--device-profile", str(self.device_profile_path), "farm-loop",
            "--empty-reference", str(self.reference), "--crop-config", str(self.crop_config), "--crop", crop.id,
            "--interval", str(self.interval.value()), "--popup-wait", str(self.popup_wait.value()),
        ]
        if self.confirm_actions.isChecked():
            worker_arguments.append("--confirm")
        if self.open_mirror.isChecked():
            worker_arguments.append("--mirror")
        if getattr(sys, "frozen", False):
            program = sys.executable
            command = ["--automation-worker", *worker_arguments]
        else:
            program = sys.executable
            command = ["-u", "-m", "plant_automation", *worker_arguments]
        self.process.setWorkingDirectory(str(Path.cwd()))
        self.process.start(program, command)
        if not self.process.waitForStarted(2500):
            QMessageBox.critical(self, "Không thể khởi động", self.process.errorString())
            return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._append_log("Bắt đầu vòng lặp: " + " ".join(command))

    def stop_automation(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._append_log("Đang gửi yêu cầu dừng an toàn…")
            self.process.terminate()

    def _read_process_output(self) -> None:
        output = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        output += bytes(self.process.readAllStandardError()).decode(errors="replace")
        for line in output.splitlines():
            self._append_log(line)

    def _automation_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._append_log("Vòng lặp đã dừng.")

    def _append_log(self, message: str) -> None:
        lines = (self.log.text() + "\n" + message).strip().splitlines()[-80:]
        self.log.setText("\n".join(lines))

def launch(initial_serial: str | None = None, device_profile_path: Path = Path("config/device-profiles/default-farm.json")) -> int:
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        dashboard = FarmDashboard(initial_serial, device_profile_path)
    except (CropConfigError, DeviceProfileError) as error:
        raise SystemExit(f"Lỗi cấu hình: {error}") from error
    dashboard.show()
    return app.exec()
