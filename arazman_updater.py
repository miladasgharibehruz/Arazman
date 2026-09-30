import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import queue
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, ProxyHandler

APP_NAME = "Arazman"


# -----------------------------
# Logging / state
# -----------------------------
def log(data_dir, message):
    try:
        path = Path(data_dir) / "update.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")
    except Exception:
        pass


def write_status(data_dir, status, **details):
    try:
        path = Path(data_dir) / "update-state.json"
        temp = path.with_suffix(".tmp")
        payload = {
            "status": status,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **details,
        }
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)
    except Exception:
        pass


# -----------------------------
# Windows helpers
# -----------------------------
def wait_pid(pid, timeout=60):
    if not pid or os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, int(pid))
    if not handle:
        if ctypes.get_last_error() == 87:
            return True
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        result = kernel.WaitForSingleObject(handle, int(timeout * 1000))
        if result == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        return result == 0
    finally:
        kernel.CloseHandle(handle)


def elevate_if_needed(argv):
    if os.name != "nt":
        return False

    try:
        import ctypes

        if ctypes.windll.shell32.IsUserAnAdmin():
            return False

        params = subprocess.list2cmdline(argv)
        rc = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,
        )
        if rc > 32:
            return True
    except Exception:
        pass

    return False


def set_app_user_model_id():
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Arazman.Updater"
        )
    except Exception:
        pass


# -----------------------------
# File operations
# -----------------------------
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_tree(src, dst):
    src = Path(src)
    dst = Path(dst)

    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)

    shutil.copytree(src, dst)


def safe_backup(install_dir, data_dir, version):
    root = Path(data_dir) / "versions"
    root.mkdir(parents=True, exist_ok=True)

    safe_version = "".join(
        c for c in str(version)
        if c.isalnum() or c in ".-_"
    ) or "previous"

    dst = root / f"{safe_version}__{time.strftime('%Y%m%d-%H%M%S')}"
    suffix = 1

    while dst.exists():
        dst = root / (
            f"{safe_version}__{time.strftime('%Y%m%d-%H%M%S')}-{suffix}"
        )
        suffix += 1

    copy_tree(install_dir, dst / "app")

    data_snapshot = dst / "data"
    data_snapshot.mkdir(parents=True, exist_ok=True)

    excluded = {
        "versions",
        "backups",
        "Updater",
        "update.log",
        "installer.log",
        "startup-error.log",
        "update-state.json",
    }

    for item in Path(data_dir).iterdir():
        if item.name in excluded:
            continue

        target = data_snapshot / item.name

        if item.is_dir():
            shutil.copytree(item, target)
        elif item.is_file():
            shutil.copy2(item, target)

    (dst / "backup.json").write_text(
        json.dumps(
            {
                "version": str(version),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "app_backup": "app",
                "data_backup": "data",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    dirs = sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old in dirs[3:]:
        shutil.rmtree(old, ignore_errors=True)

    return dst


# -----------------------------
# Download with real progress
# -----------------------------
def download(url, out, progress_callback=None, cancel_event=None):
    req = Request(
        url,
        headers={
            "User-Agent": "Arazman-Updater/2.1",
            "Accept": "application/octet-stream",
        },
    )

    try:
        response = urlopen(req, timeout=60)
    except Exception as first_error:
        try:
            response = build_opener(ProxyHandler({})).open(
                req,
                timeout=60,
            )
        except Exception as direct_error:
            raise RuntimeError(
                f"دانلود معمول: {first_error} | "
                f"دانلود مستقیم: {direct_error}"
            ) from direct_error

    total = 0

    try:
        total = int(response.headers.get("Content-Length") or 0)
    except Exception:
        total = 0

    downloaded = 0

    with response as r, open(out, "wb") as f:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("به‌روزرسانی لغو شد.")

            b = r.read(1024 * 1024)
            if not b:
                break

            f.write(b)
            downloaded += len(b)

            if progress_callback:
                progress_callback(downloaded, total)

    if progress_callback:
        progress_callback(downloaded, total)

    return downloaded, total


# -----------------------------
# Installer / rollback
# -----------------------------
def run_installer(installer, data_dir):
    install_log = Path(data_dir) / "installer.log"

    common = [
        "/NORESTART",
        "/NOCLOSEAPPLICATIONS",
        "/SP-",
        f"/LOG={install_log}",
    ]

    quiet = [
        str(installer),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        *common,
    ]

    rc = subprocess.run(
        quiet,
        check=False,
    ).returncode

    log(data_dir, f"Silent installer exit code: {rc}")

    if rc == 0:
        return 0

    log(
        data_dir,
        "Silent installation failed; starting visible installer retry",
    )

    visible = [
        str(installer),
        *common,
    ]

    rc = subprocess.run(
        visible,
        check=False,
    ).returncode

    log(data_dir, f"Visible installer exit code: {rc}")
    return rc


def rollback(backup, install_dir):
    backup = Path(backup)
    install_dir = Path(install_dir)

    if not backup.exists():
        raise RuntimeError("پشتیبان نسخه قبلی پیدا نشد.")

    app_backup = backup / "app"

    if not app_backup.exists():
        app_backup = backup

    tmp = install_dir.parent / (install_dir.name + ".rollback-temp")

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    copy_tree(app_backup, tmp)

    old = install_dir.parent / (install_dir.name + ".rollback-old")

    if old.exists():
        shutil.rmtree(old, ignore_errors=True)

    install_dir.rename(old)
    tmp.rename(install_dir)

    shutil.rmtree(old, ignore_errors=True)


# -----------------------------
# GUI
# -----------------------------
class UpdateWindow:
    def __init__(self, args):
        self.args = args
        self.root = None
        self.progress = None
        self.percent_label = None
        self.status_label = None
        self.detail_label = None
        self.version_label = None
        self.spinner = None
        self.queue = queue.Queue()
        self.worker_done = False
        self.cancel_event = threading.Event()
        self._spin_index = 0

    def build(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk

        self.root = tk.Tk()
        self.root.title("Arazman — به‌روزرسانی")
        self.root.geometry("520x300")
        self.root.resizable(False, False)
        self.root.configure(bg="#07111f")

        set_app_user_model_id()

        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception:
            pass

        outer = tk.Frame(
            self.root,
            bg="#07111f",
            padx=28,
            pady=24,
        )
        outer.pack(fill="both", expand=True)

        title = tk.Label(
            outer,
            text="به‌روزرسانی Arazman",
            bg="#07111f",
            fg="#e8f1ff",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(anchor="e")

        self.version_label = tk.Label(
            outer,
            text=f"نسخه فعلی: {self.args.current_version or '—'}    ←    نسخه جدید: {self.args.version or '—'}",
            bg="#07111f",
            fg="#70d9ff",
            font=("Segoe UI", 11, "bold"),
        )
        self.version_label.pack(anchor="e", pady=(8, 18))

        self.status_label = tk.Label(
            outer,
            text="در حال آماده‌سازی به‌روزرسانی...",
            bg="#07111f",
            fg="#ffffff",
            font=("Segoe UI", 11),
        )
        self.status_label.pack(anchor="e")

        self.progress = ttk.Progressbar(
            outer,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=464,
        )
        self.progress.pack(fill="x", pady=(14, 8))

        self.percent_label = tk.Label(
            outer,
            text="0%",
            bg="#07111f",
            fg="#25d7ff",
            font=("Segoe UI", 16, "bold"),
        )
        self.percent_label.pack(anchor="center")

        self.detail_label = tk.Label(
            outer,
            text="لطفاً تا رسیدن نوار پیشرفت به 100٪ صبر کنید.",
            bg="#07111f",
            fg="#8ea6c0",
            font=("Segoe UI", 9),
        )
        self.detail_label.pack(anchor="center", pady=(10, 0))

        self.spinner = tk.Label(
            outer,
            text="",
            bg="#07111f",
            fg="#25d7ff",
            font=("Segoe UI", 10),
        )
        self.spinner.pack(anchor="center", pady=(6, 0))

        self.root.after(80, self.process_queue)
        self.root.after(120, self.animate_spinner)

    def set_progress(self, value, status=None, detail=None):
        self.queue.put(
            (
                "progress",
                float(max(0, min(100, value))),
                status,
                detail,
            )
        )

    def set_stage(self, value, status, detail=None):
        self.queue.put(
            (
                "stage",
                float(max(0, min(100, value))),
                status,
                detail,
            )
        )

    def process_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()

                kind = item[0]

                if kind in ("progress", "stage"):
                    value = item[1]
                    status = item[2]
                    detail = item[3]

                    if self.progress:
                        self.progress["value"] = value

                    if self.percent_label:
                        self.percent_label.config(
                            text=f"{int(round(value))}%"
                        )

                    if status and self.status_label:
                        self.status_label.config(text=status)

                    if detail is not None and self.detail_label:
                        self.detail_label.config(text=detail)

                elif kind == "success":
                    self.progress["value"] = 100
                    self.percent_label.config(text="100%")
                    self.status_label.config(
                        text="به‌روزرسانی با موفقیت انجام شد."
                    )
                    self.detail_label.config(
                        text="نسخه جدید Arazman در حال اجراست..."
                    )
                    self.spinner.config(text="✓")
                    self.root.after(900, self.root.destroy)

                elif kind == "error":
                    self.status_label.config(
                        text="به‌روزرسانی ناموفق بود."
                    )
                    self.detail_label.config(
                        text=item[1]
                    )
                    self.spinner.config(text="✕")
                    self.progress["value"] = max(
                        0,
                        min(100, float(self.progress["value"])),
                    )

        except queue.Empty:
            pass

        if self.root and self.root.winfo_exists():
            self.root.after(80, self.process_queue)

    def animate_spinner(self):
        if not self.root:
            return

        frames = ["•", "••", "•••", "••", "•"]
        self._spin_index = (self._spin_index + 1) % len(frames)

        if self.spinner:
            self.spinner.config(text=frames[self._spin_index])

        if self.root.winfo_exists():
            self.root.after(300, self.animate_spinner)

    def on_close(self):
        # We deliberately do not terminate the worker.
        # Closing the window must not corrupt an installation already in progress.
        if self.worker_done:
            self.root.destroy()
            return

        try:
            self.status_label.config(
                text="به‌روزرسانی در حال انجام است؛ لطفاً صبر کنید."
            )
            self.detail_label.config(
                text="برای جلوگیری از خراب شدن برنامه، این پنجره را نبندید."
            )
        except Exception:
            pass

    def start(self, worker):
        self.build()

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )
        thread.start()

        self.root.mainloop()


# -----------------------------
# Update workflow
# -----------------------------
def perform_update(args, ui):
    data_dir = Path(args.data_dir).resolve()
    install_dir = Path(args.install_dir).resolve()

    try:
        log(
            data_dir,
            "Updater started: "
            f"update={args.update}, rollback={args.rollback}, "
            f"current={args.current_version}, target={args.version}",
        )

        write_status(
            data_dir,
            "started",
            current=args.current_version,
            target=args.version,
            progress=0,
            stage="preparing",
        )

        ui.set_stage(
            2,
            "در حال آماده‌سازی به‌روزرسانی...",
            "در حال بررسی نسخه فعلی و آماده‌سازی فایل‌های لازم.",
        )

        if not wait_pid(int(args.pid or 0), timeout=30):
            raise RuntimeError(
                "نسخه قبلی Arazman به‌طور کامل بسته نشد؛ "
                "به‌روزرسانی متوقف شد."
            )

        ui.set_stage(
            6,
            "در حال ایجاد پشتیبان...",
            "قبل از نصب نسخه جدید، یک بکاپ ایمن ساخته می‌شود.",
        )

        if args.rollback:
            log(
                data_dir,
                f"Restoring application backup: {args.backup}",
            )

            ui.set_stage(
                20,
                "در حال بازگردانی نسخه قبلی...",
                "فایل‌های نسخه پشتیبان در حال جایگزینی هستند.",
            )

            rollback(args.backup, install_dir)

            ui.set_stage(
                100,
                "بازگردانی با موفقیت انجام شد.",
                "Arazman در حال راه‌اندازی مجدد است.",
            )

        elif args.update:
            version = str(args.version or "").strip() or "unknown"

            backup_path = safe_backup(
                install_dir,
                data_dir,
                version=str(args.current_version or "previous"),
            )

            log(
                data_dir,
                f"Application and user-data backup created: {backup_path}",
            )

            write_status(
                data_dir,
                "downloading",
                current=args.current_version,
                target=version,
                backup=backup_path.name,
                progress=10,
                stage="downloading",
            )

            ui.set_stage(
                10,
                "در حال دانلود نسخه جدید...",
                f"نسخه {version} از GitHub در حال دریافت است.",
            )

            with tempfile.TemporaryDirectory(
                prefix="arazman-update-"
            ) as td:
                installer = Path(td) / "Arazman-Setup.exe"

                def download_progress(downloaded, total):
                    if total > 0:
                        ratio = downloaded / total
                        overall = 10 + (ratio * 55)
                        percent = int(round(ratio * 100))

                        detail = (
                            f"دانلود: {percent}%"
                            f" — {downloaded / 1048576:.1f} MB"
                        )

                        if total:
                            detail += (
                                f" از {total / 1048576:.1f} MB"
                            )

                        ui.set_progress(
                            overall,
                            "در حال دانلود نسخه جدید...",
                            detail,
                        )

                        write_status(
                            data_dir,
                            "downloading",
                            current=args.current_version,
                            target=version,
                            backup=backup_path.name,
                            progress=int(round(overall)),
                            stage="downloading",
                            downloaded=downloaded,
                            total=total,
                        )
                    else:
                        ui.set_progress(
                            10,
                            "در حال دانلود نسخه جدید...",
                            f"دریافت شده: {downloaded / 1048576:.1f} MB",
                        )

                log(
                    data_dir,
                    f"Downloading release {version} from GitHub",
                )

                download(
                    args.url,
                    installer,
                    progress_callback=download_progress,
                    cancel_event=ui.cancel_event,
                )

                ui.set_stage(
                    67,
                    "در حال بررسی صحت فایل...",
                    "SHA-256 فایل دانلودشده در حال بررسی است.",
                )

                write_status(
                    data_dir,
                    "verifying",
                    current=args.current_version,
                    target=version,
                    backup=backup_path.name,
                    progress=67,
                    stage="verifying",
                )

                if args.sha256:
                    got = sha256(installer).lower()
                    expected = (
                        str(args.sha256)
                        .strip()
                        .lower()
                        .replace("sha256:", "")
                    )

                    if got != expected:
                        raise RuntimeError(
                            "صحت فایل به‌روزرسانی تأیید نشد؛ "
                            "نصب متوقف شد."
                        )

                    log(
                        data_dir,
                        "SHA-256 verification succeeded",
                    )

                ui.set_stage(
                    72,
                    "فایل تأیید شد؛ نصب در حال شروع است...",
                    "نصاب نسخه جدید Arazman اجرا می‌شود.",
                )

                write_status(
                    data_dir,
                    "installing",
                    current=args.current_version,
                    target=version,
                    backup=backup_path.name,
                    progress=72,
                    stage="installing",
                )

                # Inno Setup does not expose a reliable percentage to the
                # updater process. Therefore 72% is the exact completed
                # workflow boundary, and the installer phase is represented
                # as an active stage rather than a fake download percentage.
                rc = run_installer(installer, data_dir)

                if rc != 0:
                    raise RuntimeError(
                        f"نصب نسخه جدید با کد {rc} تمام شد."
                    )

                ui.set_stage(
                    95,
                    "نصب کامل شد؛ در حال تکمیل...",
                    "فایل‌های به‌روزرسانی با موفقیت نصب شدند.",
                )

                log(
                    data_dir,
                    f"Release {version} installed successfully",
                )

                write_status(
                    data_dir,
                    "success",
                    current=args.current_version,
                    target=version,
                    backup=backup_path.name,
                    progress=100,
                    stage="completed",
                )

        exe = install_dir / "Arazman.exe"

        ui.set_stage(
            98,
            "در حال راه‌اندازی Arazman...",
            "لطفاً چند لحظه صبر کنید.",
        )

        if exe.exists():
            subprocess.Popen(
                [str(exe)],
                cwd=str(install_dir),
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )

        ui.set_stage(
            100,
            "به‌روزرسانی با موفقیت انجام شد.",
            "نسخه جدید Arazman اجرا شد.",
        )

        ui.queue.put(("success",))
        ui.worker_done = True

        return 0

    except Exception as exc:
        log(
            data_dir,
            f"ERROR: {type(exc).__name__}: {exc}",
        )

        write_status(
            data_dir,
            "failed",
            current=args.current_version,
            target=args.version,
            error=str(exc),
            progress=0,
            stage="failed",
        )

        ui.queue.put(("error", str(exc)))
        ui.worker_done = True

        return 1


def main():
    set_app_user_model_id()

    ap = argparse.ArgumentParser(add_help=False)

    ap.add_argument("--update", action="store_true")
    ap.add_argument("--rollback", action="store_true")

    ap.add_argument("--pid")
    ap.add_argument("--install-dir", required=True)
    ap.add_argument("--data-dir", required=True)

    ap.add_argument("--url")
    ap.add_argument("--version")
    ap.add_argument("--current-version")
    ap.add_argument("--sha256")
    ap.add_argument("--backup")

    args = ap.parse_args()

    # UAC must happen before the GUI starts so the elevated process owns
    # the visible update window.
    if elevate_if_needed(sys.argv[1:]):
        return 0

    ui = UpdateWindow(args)

    return_code = {"value": 1}

    def worker():
        return_code["value"] = perform_update(args, ui)

    ui.start(worker)

    return return_code["value"]


if __name__ == "__main__":
    raise SystemExit(main())
