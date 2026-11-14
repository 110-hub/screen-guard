# -*- coding: utf-8 -*-
"""屏幕管控 · 单文件安装程序（PyInstaller onefile 打包，内置 payload.zip）。

用法：
  双击运行            → 图形界面安装
  安装程序.exe --silent → 无界面安装（自动化 / 排障用）
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import zipfile
from tkinter import ttk

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import winutil

APP_TITLE = "屏幕管控 · 安装程序"
BG = "#171717"
CARD = "#212121"
CARD_LIGHT = "#2c2c2c"
LINE = "#393939"
TEXT = "#ececec"
MUTED = "#9d9d9d"
ACCENT = "#4e8cff"
ACCENT_HOVER = "#6a9bff"
OK = "#55c9a5"
ERR = "#f07480"

TARGET_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                          "Programs", "ScreenGuard")
_MEIPASS = getattr(sys, "_MEIPASS", _ROOT)
PAYLOAD_ZIP = os.path.join(_MEIPASS, "payload.zip")
PAYLOAD_DIR = os.path.join(_MEIPASS, "payload")      # 开发模式下的散装目录
if not getattr(sys, "frozen", False):                 # 源码调试时用构建产物
    if os.path.exists(os.path.join(_ROOT, "build", "payload.zip")):
        PAYLOAD_ZIP = os.path.join(_ROOT, "build", "payload.zip")
    elif os.path.isdir(os.path.join(_ROOT, "dist", "ScreenGuard")):
        PAYLOAD_DIR = os.path.join(_ROOT, "dist", "ScreenGuard")
EXE_NAME = winutil.EXE_NAME


def font(size, weight="normal"):
    return ("Microsoft YaHei UI", size, weight)


# ----------------------------- 安装核心 -----------------------------
def payload_ready():
    return os.path.exists(PAYLOAD_ZIP) or os.path.isdir(PAYLOAD_DIR)


def count_payload_files():
    if os.path.exists(PAYLOAD_ZIP):
        with zipfile.ZipFile(PAYLOAD_ZIP) as zf:
            return max(1, sum(1 for n in zf.namelist() if not n.endswith("/")))
    return max(1, sum(len(files) for _, _, files in os.walk(PAYLOAD_DIR)))


LOG_PATH = os.path.join(tempfile.gettempdir(), "screenguard_setup.log")


def log_line(text):
    """静默安装没有控制台，进度与错误写到临时日志。"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + text + "\n")
    except OSError:
        pass


def _with_retry(call, attempts=8, delay=0.7):
    """刚结束的旧程序或杀毒软件可能短暂占用文件，失败时重试。"""
    last = None
    for _ in range(attempts):
        try:
            return call()
        except PermissionError as exc:
            last = exc
            time.sleep(delay)
    raise last


def do_install(status=None, progress=None, with_desktop=True, with_startup=True):
    """把程序装到 TARGET_DIR 并注册快捷方式/自启/卸载信息，返回 exe 路径。"""
    status = status or (lambda *a, **k: None)
    progress = progress or (lambda *a, **k: None)

    status("正在结束已运行的旧实例...")
    winutil.stop_running_app()
    time.sleep(0.8)          # 等待文件句柄释放

    total = count_payload_files()
    os.makedirs(TARGET_DIR, exist_ok=True)
    done = 0

    if os.path.exists(PAYLOAD_ZIP):
        status("正在解压程序文件（共 %d 个）..." % total)
        with zipfile.ZipFile(PAYLOAD_ZIP) as zf:
            for info in zf.infolist():
                if info.filename.endswith("/"):
                    continue
                rel = info.filename.replace("/", os.sep)
                target = os.path.join(TARGET_DIR, rel)
                if rel.split(os.sep)[0].lower() == "data" and os.path.exists(target):
                    continue                     # 不覆盖已有学习数据，只补新增词库
                os.makedirs(os.path.dirname(target), exist_ok=True)

                def write_entry(entry=info, dest=target):
                    try:
                        with zf.open(entry) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                    except PermissionError as exc:
                        raise PermissionError(exc.errno, exc.strerror, dest)

                _with_retry(write_entry)
                done += 1
                if done % 40 == 0:
                    progress(min(85, done * 85.0 / total))
                    status("正在解压程序文件... %d / %d" % (done, total))
    else:
        status("正在复制程序文件（共 %d 个）..." % total)
        for base, _, files in os.walk(PAYLOAD_DIR):
            rel_dir = os.path.relpath(base, PAYLOAD_DIR)
            out_dir = TARGET_DIR if rel_dir == "." else os.path.join(TARGET_DIR, rel_dir)
            os.makedirs(out_dir, exist_ok=True)
            is_data = rel_dir.split(os.sep)[0].lower() == "data"
            for name in files:
                target = os.path.join(out_dir, name)
                if is_data and os.path.exists(target):
                    continue
                _with_retry(lambda b=base, n=name, t=target: shutil.copy2(os.path.join(b, n), t))
                done += 1
                if done % 40 == 0:
                    progress(min(85, done * 85.0 / total))
                    status("正在复制程序文件... %d / %d" % (done, total))

    exe_path = os.path.join(TARGET_DIR, EXE_NAME)
    progress(88)
    status("正在创建快捷方式与开机启动项...")
    winutil.create_all_shortcuts(exe_path, with_desktop=with_desktop,
                                 with_startmenu=True, with_startup=with_startup)

    progress(95)
    status("正在写入卸载信息...")
    winutil.write_uninstall_registry(TARGET_DIR, exe_path)

    progress(100)
    return exe_path


# ----------------------------- 图形界面 -----------------------------
class SetupApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        width = 620
        screen = self.root.winfo_screenwidth()
        self.root.geometry("%dx430+%d+120" % (width, max(0, int((screen - width) / 2))))
        self.root.resizable(False, False)
        try:
            icon = os.path.join(_MEIPASS, "icon.ico")
            if os.path.exists(icon):
                self.root.iconbitmap(icon)
        except tk.TclError:
            pass

        self.var_desktop = tk.BooleanVar(value=True)
        self.var_startup = tk.BooleanVar(value=True)
        self.var_launch = tk.BooleanVar(value=True)
        self.installing = False
        self._build()

    def _build(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=CARD_LIGHT,
                        borderwidth=0, thickness=6, lightcolor=ACCENT, darkcolor=ACCENT)

        header = tk.Frame(self.root, bg=CARD, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="屏幕管控 · 英语单词锁屏", bg=CARD, fg=TEXT,
                 font=font(16, "bold")).pack(anchor="w", padx=26, pady=(18, 2))
        tk.Label(header, text="按周期弹出中文释义，拼写正确英文后才能继续使用电脑",
                 bg=CARD, fg=MUTED, font=font(9)).pack(anchor="w", padx=26)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=26, pady=16)

        tk.Label(body, text="安装位置", bg=BG, fg=MUTED, font=font(9)).pack(anchor="w")
        tk.Label(body, text=TARGET_DIR, bg=CARD, fg=TEXT, font=font(9), anchor="w",
                 padx=12, pady=8, highlightthickness=1,
                 highlightbackground=LINE).pack(fill="x", pady=(4, 14))

        opts = tk.Frame(body, bg=BG)
        opts.pack(anchor="w")
        for var, text in ((self.var_desktop, "创建桌面快捷方式"),
                          (self.var_startup, "开机自动启动（静默驻留托盘）"),
                          (self.var_launch, "安装完成后立即运行")):
            tk.Checkbutton(opts, text=text, variable=var, bg=BG, fg=TEXT,
                           selectcolor=CARD_LIGHT, activebackground=BG, activeforeground=TEXT,
                           font=font(10), bd=0, highlightthickness=0,
                           cursor="hand2").pack(anchor="w", pady=3)

        self.progress = ttk.Progressbar(body, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(16, 8))
        self.status_label = tk.Label(body, text="准备就绪，点击「开始安装」。", bg=BG, fg=MUTED,
                                     font=font(9), anchor="w")
        self.status_label.pack(fill="x")

        buttons = tk.Frame(self.root, bg=BG)
        buttons.pack(fill="x", padx=26, pady=(0, 20))
        self.btn_install = tk.Button(buttons, text="开始安装", command=self._start,
                                     bg=ACCENT, fg="#ffffff", relief="flat", bd=0,
                                     font=font(11, "bold"), padx=28, pady=10,
                                     cursor="hand2", activebackground=ACCENT_HOVER,
                                     activeforeground="#ffffff")
        self.btn_install.pack(side="left")
        self.btn_close = tk.Button(buttons, text="关闭", command=self.root.destroy,
                                   bg=CARD_LIGHT, fg=TEXT, relief="flat", bd=0,
                                   font=font(10), padx=22, pady=10, cursor="hand2",
                                   activebackground=LINE, activeforeground=TEXT)
        self.btn_close.pack(side="left", padx=(10, 0))

    def _status(self, text, color=MUTED):
        """安装在工作线程执行，界面更新必须切回主线程。"""
        self.root.after(0, self._apply_status, text, color)

    def _apply_status(self, text, color=MUTED):
        self.status_label.config(text=text, fg=color)

    def _progress(self, value):
        self.root.after(0, self._apply_progress, value)

    def _apply_progress(self, value):
        self.progress["value"] = value

    def _start(self):
        if self.installing:
            return
        if not payload_ready():
            self._status("安装包损坏：未找到程序数据（payload.zip）。", ERR)
            return
        self.installing = True
        self.btn_install.config(state="disabled", text="正在安装...")
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        try:
            exe_path = do_install(status=self._status, progress=self._progress,
                                  with_desktop=self.var_desktop.get(),
                                  with_startup=self.var_startup.get())
            self.root.after(0, self._finish_ok, exe_path)
        except Exception as exc:                 # 安装失败要提示，不能静默退出
            self.root.after(0, self._finish_fail, str(exc))

    def _finish_ok(self, exe_path):
        self.installing = False
        self.btn_install.config(state="normal", text="重新安装")
        self._status("安装完成，可关闭本窗口。", OK)
        if self.var_launch.get():
            try:
                subprocess.Popen([exe_path], close_fds=True)
            except OSError:
                pass

    def _finish_fail(self, message):
        self.installing = False
        self.btn_install.config(state="normal", text="重试安装")
        self._status("安装失败：" + message, ERR)

    def run(self):
        self.root.mainloop()


def main():
    if not payload_ready():
        log_line("安装包损坏：缺少 payload.zip")
        return 1
    if "--silent" in sys.argv:
        log_line("开始静默安装")
        try:
            exe_path = do_install(status=log_line, progress=lambda v: None)
        except Exception as exc:
            log_line("安装失败：%r 文件=%s" % (exc, getattr(exc, "filename", "")))
            return 1
        log_line("安装完成：%s" % exe_path)
        return 0
    SetupApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
