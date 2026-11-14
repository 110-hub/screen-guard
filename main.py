# -*- coding: utf-8 -*-
"""屏幕管控 · 初中英语单词锁屏后台

启动方式：双击 run.bat / 安装后的 ScreenGuard.exe，或执行  pythonw main.py
"""
import ctypes
import logging
import os
import sys
import time
import traceback
import tkinter as tk
from tkinter import messagebox

import admin
import config
import quiz
import tray as tray_mod
import winutil
from progress import Progress
from wordbank import WordBank

MUTEX_NAME = "Global\\ScreenGuard_EnglishWordLock_SingleInstance"


def setup_logging():
    """异常写入 data/app.log，方便排查（打包后无控制台）。"""
    config.ensure_dirs()
    log_path = os.path.join(config.DATA_DIR, "app.log")
    try:
        logging.basicConfig(filename=log_path, level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    except OSError:
        return

    def excepthook(exc_type, exc, tb):
        logging.error("未捕获异常:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = excepthook


def already_running():
    """用命名互斥体判断是否已有实例在常驻（返回 True 表示已有实例）。"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return kernel32.GetLastError() == 183   # ERROR_ALREADY_EXISTS


class Controller:
    """负责定时调度、弹窗生命周期与设置持久化。"""

    def __init__(self):
        config.ensure_dirs()
        config.seed_words()
        self.root = tk.Tk()
        self.root.title("屏幕管控")
        self.root.withdraw()

        self.settings = config.load_settings()
        self.bank = WordBank()
        self.bank.load()
        self.progress = Progress()

        self.quiz_window = None
        self.admin_window = None
        self.tray = None
        self.paused_until = 0.0
        self.next_due = time.time() + int(self.settings.get("interval_minutes", 10)) * 60

    # ----------------------------- 生命周期 -----------------------------
    def start(self, show_window=True):
        self.root.report_callback_exception = self._log_exception
        if show_window:
            self.admin_window = admin.AdminWindow(self)
        self.tray = tray_mod.Tray(self)
        self.tray.start()
        logging.info("程序启动，词库 %d 词", self.bank.total())
        self.root.after(1000, self.tick)
        self.root.mainloop()

    @staticmethod
    def _log_exception(exc_type, exc, tb):
        logging.error("界面回调异常:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    # ----------------------------- 后台窗口 -----------------------------
    def show_admin(self):
        win = self.admin_window
        try:
            if win is not None and win.winfo_exists():
                win.deiconify()
                win.lift()
                win.focus_force()
                win._refresh_status()
                return
        except tk.TclError:
            pass
        self.admin_window = admin.AdminWindow(self)

    def hide_admin(self):
        if self.admin_window is None:
            return
        try:
            self.admin_window.withdraw()
        except tk.TclError:
            pass
        if self.tray is not None:
            self.tray.notify("后台窗口已隐藏，程序仍在后台管控。\n双击托盘图标可重新打开。")

    def request_quit(self):
        """托盘菜单或关闭窗口时的退出请求，需通过密码校验。"""
        import ui_common
        parent = self.admin_window if self.admin_window is not None else self.root
        try:
            if self.admin_window is not None:
                self.admin_window.deiconify()
                self.admin_window.lift()
        except tk.TclError:
            pass
        ok, _ = ui_common.ask_password(parent, self.settings, tip="退出屏幕管控需要家长密码")
        if ok:
            self.quit_app()

    def quit_app(self):
        try:
            self.progress.save()
        except OSError:
            pass
        if self.quiz_window is not None:
            self.quiz_window._close()
        if self.tray is not None:
            self.tray.stop()
        self.root.destroy()

    # ----------------------------- 调度 -----------------------------
    def tick(self):
        try:
            now = time.time()
            if (self.settings.get("enabled")
                    and self.quiz_window is None
                    and now >= self.paused_until
                    and now >= self.next_due):
                self.trigger_quiz()
            if self.tray is not None:
                _, text = self.status()
                self.tray.update_title("屏幕管控 · " + text)
        except Exception:
            logging.exception("调度异常")
        finally:
            self.root.after(1000, self.tick)

    def trigger_quiz(self, manual=False):
        if self.quiz_window is not None:
            return
        count = int(self.settings.get("words_per_quiz", 1))
        words = self.bank.pick(self.settings.get("scope", "all"), self.progress, count)
        if not words:
            if manual:
                messagebox.showwarning(
                    "没有可出的题",
                    "当前出题范围内没有单词。\n请检查 data/words 目录下的词库文件，"
                    "或把出题范围改回「全部词库」。", parent=self.admin_window or self.root)
            return
        self.quiz_window = quiz.QuizOverlay(self.root, self, words)

    def on_quiz_finished(self, window):
        self.quiz_window = None
        self.next_due = time.time() + int(self.settings.get("interval_minutes", 10)) * 60
        if self.admin_window is not None:
            self.admin_window._refresh_status()

    def on_quiz_skipped(self, window, pause_minutes):
        self.quiz_window = None
        self.paused_until = time.time() + max(0, pause_minutes) * 60
        self.next_due = self.paused_until
        if self.admin_window is not None:
            self.admin_window._refresh_status()

    def pause_minutes(self, minutes):
        self.paused_until = time.time() + max(0, minutes) * 60
        self.next_due = self.paused_until

    def resume(self):
        self.paused_until = 0.0
        self.next_due = time.time() + int(self.settings.get("interval_minutes", 10)) * 60

    # ----------------------------- 设置 -----------------------------
    def apply_settings(self):
        config.save_settings(self.settings)
        self.next_due = time.time() + int(self.settings.get("interval_minutes", 10)) * 60

    def reload_bank(self):
        return self.bank.load()

    # ----------------------------- 状态文本 -----------------------------
    def status(self):
        if not self.settings.get("enabled"):
            return "disabled", "管控已关闭"
        now = time.time()
        if now < self.paused_until:
            return "paused", "已暂停（剩 %d 分钟）" % int((self.paused_until - now) / 60 + 1)
        if self.quiz_window is not None:
            return "paused", "答题中"
        return "running", "管控中"

    def countdown_text(self):
        if not self.settings.get("enabled"):
            return "· 打开开关并保存后开始计时"
        if self.quiz_window is not None:
            return "· 请先完成答题"
        now = time.time()
        if now < self.paused_until:
            left = int(self.paused_until - now)
            return "· 暂停中，%02d:%02d 后恢复" % (left // 60, left % 60)
        left = max(0, int(self.next_due - now))
        return "· 距下次弹窗 %02d:%02d（每 %d 分钟一次）" % (
            left // 60, left % 60, int(self.settings.get("interval_minutes", 10)))


def run_uninstall():
    """卸载：清快捷方式/自启/注册表，退出后删除安装目录。"""
    setup_logging()
    root = tk.Tk()
    root.withdraw()
    settings = config.load_settings()
    if settings.get("password_hash"):
        import ui_common
        ok, _ = ui_common.ask_password(root, settings, tip="卸载屏幕管控需要家长密码")
        if not ok:
            root.destroy()
            return
    if not messagebox.askyesno("卸载屏幕管控",
                               "确定卸载「屏幕管控」吗？\n"
                               "程序、设置、学习记录与错词本都会被删除。"):
        root.destroy()
        return
    root.destroy()

    config.apply_autostart(False)
    winutil.remove_shortcuts()
    winutil.remove_uninstall_registry()
    winutil.schedule_dir_removal(config.BASE_DIR, delay=3)
    logging.info("已执行卸载清理，等待退出后删除目录 %s", config.BASE_DIR)


def main():
    setup_logging()
    if "--uninstall" in sys.argv:
        run_uninstall()
        return
    if sys.platform != "win32":
        print("本程序面向 Windows 桌面环境（依赖 tkinter 全屏窗口）。")
    if already_running():
        tip_root = tk.Tk()
        tip_root.withdraw()
        messagebox.showinfo(
            "屏幕管控",
            "程序已在后台常驻运行。\n请双击系统托盘中的蓝色图标打开后台。")
        tip_root.destroy()
        return
    controller = Controller()
    if not controller.bank.total():
        messagebox.showwarning(
            "词库为空",
            "没有找到词库文件。\n请把 words_*.txt 放到 data/words 目录下"
            "（格式：word|pos|含义|grade）。")
    controller.start(show_window="--silent" not in sys.argv)


if __name__ == "__main__":
    main()
