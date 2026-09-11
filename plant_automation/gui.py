"""Giao diện desktop tối giản cho vòng lặp chăm sóc ruộng."""

from __future__ import annotations

from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .adb import AndroidBridge, AdbError
from .crops import CropConfigError, CropProfile, load_crops


class FarmApp(tk.Tk):
    def __init__(self, initial_serial: str | None = None) -> None:
        super().__init__()
        self.title("Plant Automation")
        self.minsize(820, 650)
        self.geometry("920x720")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.serial = tk.StringVar(value=initial_serial or "")
        self.reference = tk.StringVar(value="captures/empty-reference.png")
        self.crop_config = Path("config/crops.json")
        self.crops = load_crops(self.crop_config)
        self.crop_options = {f"{crop.name} ({crop.id})": crop for crop in self.crops}
        self.crop_display = tk.StringVar(value=next(iter(self.crop_options)))
        self.interval = tk.StringVar(value="3")
        self.popup_wait = tk.StringVar(value="5")
        self.open_mirror = tk.BooleanVar(value=True)
        self.confirm_actions = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Chưa chạy")
        self.action_mode = tk.StringVar()
        self.process: subprocess.Popen[str] | None = None
        self.output: queue.Queue[str] = queue.Queue()

        self._configure_styles()
        self._build()
        self.confirm_actions.trace_add("write", self._update_action_mode)
        self._update_action_mode()
        self.after(100, self._drain_output)
        self._refresh_devices()

    def _configure_styles(self) -> None:
        self.configure(background="#eef3f8")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#eef3f8")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Card.TLabelframe", background="#ffffff", foreground="#334155", borderwidth=0)
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#475569", font=("TkDefaultFont", 10, "bold"))
        style.configure("Title.TLabel", background="#eef3f8", foreground="#0f172a", font=("TkDefaultFont", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#eef3f8", foreground="#64748b", font=("TkDefaultFont", 10))
        style.configure("Section.TLabel", background="#ffffff", foreground="#334155", font=("TkDefaultFont", 10, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#64748b")
        style.configure("Status.TLabel", background="#e2e8f0", foreground="#334155", padding=(10, 6))
        style.configure("Primary.TButton", font=("TkDefaultFont", 10, "bold"), padding=(14, 9), background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#94a3b8")])
        style.configure("Danger.TButton", font=("TkDefaultFont", 10, "bold"), padding=(14, 9), background="#dc2626", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b91c1c"), ("disabled", "#fca5a5")])
        style.configure("Soft.TButton", padding=(10, 7), background="#e2e8f0", foreground="#334155")
        style.map("Soft.TButton", background=[("active", "#cbd5e1")])

    def _build(self) -> None:
        content = ttk.Frame(self, style="App.TFrame", padding=(24, 20))
        content.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        header = ttk.Frame(content, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ttk.Label(header, text="Plant Automation", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Trồng • tưới • thu hoạch qua ADB", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=1, rowspan=2, sticky="e")
        header.columnconfigure(0, weight=1)

        setup = ttk.LabelFrame(content, text="  Thiết lập kết nối  ", style="Card.TLabelframe", padding=16)
        setup.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        setup.columnconfigure(1, weight=1)
        ttk.Label(setup, text="Thiết bị Android", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=5)
        self.device_selector = ttk.Combobox(setup, textvariable=self.serial, state="normal")
        self.device_selector.grid(row=0, column=1, sticky="ew", padx=12, pady=5)
        ttk.Button(setup, text="Quét thiết bị", style="Soft.TButton", command=self._refresh_devices).grid(row=0, column=2, pady=5)
        ttk.Label(setup, text="Ảnh mốc đất trống", style="Section.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(setup, textvariable=self.reference).grid(row=1, column=1, sticky="ew", padx=12, pady=5)
        ttk.Button(setup, text="Chọn ảnh…", style="Soft.TButton", command=self._choose_reference).grid(row=1, column=2, pady=5)
        ttk.Label(setup, text="Cây trồng tự động", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=5)
        self.crop_selector = ttk.Combobox(setup, textvariable=self.crop_display, values=tuple(self.crop_options), state="readonly")
        self.crop_selector.grid(row=2, column=1, sticky="ew", padx=12, pady=5)
        ttk.Label(setup, text="Thêm cây trong config/crops.json", style="Muted.TLabel").grid(row=2, column=2, sticky="w", pady=5)

        controls = ttk.LabelFrame(content, text="  Điều khiển  ", style="Card.TLabelframe", padding=16)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        controls.columnconfigure(7, weight=1)
        ttk.Label(controls, text="Quét mỗi", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, width=5, textvariable=self.interval).grid(row=0, column=1, padx=(7, 2))
        ttk.Label(controls, text="giây", style="Muted.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Label(controls, text="Chờ popup", style="Section.TLabel").grid(row=0, column=3, padx=(20, 0), sticky="w")
        ttk.Entry(controls, width=5, textvariable=self.popup_wait).grid(row=0, column=4, padx=(7, 2))
        ttk.Label(controls, text="giây", style="Muted.TLabel").grid(row=0, column=5, sticky="w")
        ttk.Checkbutton(controls, text="Mở scrcpy", variable=self.open_mirror).grid(row=0, column=6, padx=(24, 0))
        ttk.Checkbutton(controls, text="Cho phép thao tác thật", variable=self.confirm_actions).grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Label(controls, textvariable=self.action_mode, style="Muted.TLabel").grid(row=1, column=3, columnspan=4, sticky="w", padx=(20, 0), pady=(12, 0))

        actions = ttk.Frame(controls, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=8, sticky="ew", pady=(16, 0))
        self.start_button = ttk.Button(actions, text="▶  Bắt đầu vòng lặp", style="Primary.TButton", command=self._start_loop)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(actions, text="■  Dừng an toàn", style="Danger.TButton", command=self._stop, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=8)
        self.inspect_button = ttk.Button(actions, text="Kiểm tra ruộng", style="Soft.TButton", command=self._inspect)
        self.inspect_button.grid(row=0, column=2, padx=(20, 8))
        self.capture_button = ttk.Button(actions, text="Lưu ảnh mốc", style="Soft.TButton", command=self._capture_reference)
        self.capture_button.grid(row=0, column=3, padx=8)

        log_card = ttk.LabelFrame(content, text="  Nhật ký hoạt động  ", style="Card.TLabelframe", padding=12)
        log_card.grid(row=3, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(0, weight=1)
        self.log = tk.Text(
            log_card,
            height=14,
            wrap="word",
            state="disabled",
            background="#0f172a",
            foreground="#dbeafe",
            insertbackground="#ffffff",
            relief="flat",
            padx=12,
            pady=10,
            font=("Menlo", 11),
        )
        self.log.grid(row=0, column=0, sticky="nsew")

    def _update_action_mode(self, *_: object) -> None:
        if self.confirm_actions.get():
            self.action_mode.set("Chế độ thật: phần mềm có thể bấm vào game")
        else:
            self.action_mode.set("Xem trước: không bấm vào game")

    def _refresh_devices(self) -> None:
        try:
            devices = [device for device in AndroidBridge.devices() if device.state == "device"]
        except AdbError as error:
            self._show_error(str(error))
            return
        values = [device.serial for device in devices]
        self.device_selector["values"] = values
        if not self.serial.get() and values:
            self.serial.set(values[0])
        self.status.set(f"Tìm thấy {len(values)} thiết bị sẵn sàng")

    def _choose_reference(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn ảnh mốc đất trống", filetypes=[("PNG", "*.png"), ("Tất cả", "*.*")]
        )
        if path:
            self.reference.set(path)

    def _validate_common(self) -> tuple[str, str] | None:
        serial = self.serial.get().strip()
        reference = self.reference.get().strip()
        if not serial:
            self._show_error("Hãy chọn hoặc nhập serial của điện thoại.")
            return None
        if not reference:
            self._show_error("Hãy chọn ảnh mốc đất trống.")
            return None
        return serial, reference

    def _selected_crop(self) -> CropProfile | None:
        crop = self.crop_options.get(self.crop_display.get())
        if crop is None:
            self._show_error("Hãy chọn một loại cây trồng hợp lệ.")
        return crop

    def _start_loop(self) -> None:
        common = self._validate_common()
        if common is None:
            return
        crop = self._selected_crop()
        if crop is None:
            return
        try:
            interval = float(self.interval.get())
            popup_wait = float(self.popup_wait.get())
        except ValueError:
            self._show_error("Thời gian quét và chờ popup phải là số.")
            return
        if interval < 1 or popup_wait < 1:
            self._show_error("Thời gian quét và chờ popup phải từ 1 giây.")
            return
        serial, reference = common
        command = [
            sys.executable, "-u", "-m", "plant_automation", "--serial", serial, "farm-loop",
            "--empty-reference", reference, "--interval", str(interval), "--popup-wait", str(popup_wait),
            "--crop-config", str(self.crop_config), "--crop", crop.id,
        ]
        if self.confirm_actions.get():
            command.append("--confirm")
        if self.open_mirror.get():
            command.append("--mirror")
        self._launch(command, "Vòng lặp đang chạy")

    def _inspect(self) -> None:
        common = self._validate_common()
        if common is None:
            return
        serial, reference = common
        self._launch(
            [sys.executable, "-u", "-m", "plant_automation", "--serial", serial, "inspect-farm", "--empty-reference", reference],
            "Đang kiểm tra ruộng",
        )

    def _capture_reference(self) -> None:
        common = self._validate_common()
        if common is None:
            return
        serial, reference = common
        if not messagebox.askyesno("Lưu ảnh mốc", "Chỉ lưu ảnh mốc khi cả 16 ô đều trống và không có popup. Tiếp tục?"):
            return
        self._launch(
            [sys.executable, "-u", "-m", "plant_automation", "--serial", serial, "capture-empty-reference", "--output", reference],
            "Đang lưu ảnh mốc",
        )

    def _launch(self, command: list[str], label: str) -> None:
        if self.process and self.process.poll() is None:
            self._show_error("Một tác vụ đang chạy. Hãy dừng trước khi bắt đầu tác vụ khác.")
            return
        try:
            self.process = subprocess.Popen(
                command,
                cwd=Path.cwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as error:
            self._show_error(f"Không thể khởi chạy tác vụ: {error}")
            return
        self.status.set(label)
        self.start_button.configure(state="disabled")
        self.inspect_button.configure(state="disabled")
        self.capture_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._append_log("$ " + " ".join(command))
        threading.Thread(target=self._read_process_output, args=(self.process,), daemon=True).start()

    def _read_process_output(self, process: subprocess.Popen[str]) -> None:
        if process.stdout:
            for line in process.stdout:
                self.output.put(line.rstrip())
        self.output.put(f"[Tác vụ kết thúc, mã {process.wait()}]")

    def _drain_output(self) -> None:
        while True:
            try:
                line = self.output.get_nowait()
            except queue.Empty:
                break
            self._append_log(line)
        if self.process and self.process.poll() is not None:
            self.status.set("Sẵn sàng")
            self.process = None
            self.start_button.configure(state="normal")
            self.inspect_button.configure(state="normal")
            self.capture_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
        self.after(100, self._drain_output)

    def _stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.status.set("Đang dừng an toàn…")
            self._append_log("Gửi yêu cầu dừng an toàn.")
            self.process.send_signal(signal.SIGINT)

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_error(self, message: str) -> None:
        self.status.set("Cần kiểm tra cấu hình")
        messagebox.showerror("Plant Automation", message)

    def _on_close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Đang chạy", "Dừng vòng lặp và đóng giao diện?"):
                return
            self._stop()
        self.destroy()


def launch(initial_serial: str | None = None) -> int:
    """Open the desktop control panel and return when it is closed."""
    try:
        app = FarmApp(initial_serial)
    except CropConfigError as error:
        raise SystemExit(f"Lỗi cấu hình cây trồng: {error}") from error
    app.mainloop()
    return 0
