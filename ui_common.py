# -*- coding: utf-8 -*-
"""界面公共样式与小组件。"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import config

# 配色（深色主题，减少屏幕刺眼）
BG = "#0f1524"
CARD = "#19223a"
CARD_LIGHT = "#243052"
ACCENT = "#4f7cff"
OK = "#22c55e"
ERR = "#f05b5b"
WARN = "#f5a524"
TEXT = "#e9eefc"
MUTED = "#93a0c0"
LINE = "#2c3859"

CN_FONT = "Microsoft YaHei UI"
EN_FONT = "Segoe UI"


def cn_family():
    families = set(tkfont.families())
    for name in (CN_FONT, "Microsoft YaHei", "SimHei", "SimSun"):
        if name in families:
            return name
    return "TkDefaultFont"


def font(size=12, weight="normal", family=None):
    return (family or cn_family(), size, weight)


def apply_ttk_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT, font=font(10))
    style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=font(10))
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=font(9))
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=font(9))
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=font(16, "bold"))
    style.configure("TButton", font=font(10), padding=(10, 6))
    style.configure("Accent.TButton", font=font(10, "bold"), padding=(12, 8))
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 6, 0, 0))
    style.configure("TNotebook.Tab", font=font(10), padding=(16, 8))
    style.configure("TCheckbutton", background=CARD, foreground=TEXT, font=font(10))
    style.configure("TRadiobutton", background=CARD, foreground=TEXT, font=font(10))
    style.configure("Treeview", font=font(10), rowheight=26, background="#101730",
                    fieldbackground="#101730", foreground=TEXT, borderwidth=0)
    style.configure("Treeview.Heading", font=font(10, "bold"), background=CARD_LIGHT,
                    foreground=TEXT, borderwidth=0)
    style.map("Treeview", background=[("selected", ACCENT)])
    style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=CARD_LIGHT,
                    borderwidth=0, thickness=10)
    return style


def center(win, width, height):
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = max(0, int((screen_w - width) / 2))
    y = max(0, int((screen_h - height) / 2.2))
    win.geometry("%dx%d+%d+%d" % (width, height, x, y))


class PasswordDialog(tk.Toplevel):
    """modal 密码输入框，返回 bool 结果。"""

    def __init__(self, parent, title="家长验证", tip="请输入家长密码", width=380, height=210):
        super().__init__(parent)
        self.value = None
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        center(self, width, height)

        wrap = tk.Frame(self, bg=BG, padx=24, pady=18)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text=tip, bg=BG, fg=TEXT, font=font(12, "bold"),
                 anchor="w").pack(fill="x")
        self.entry = tk.Entry(wrap, show="*", font=font(13), width=22,
                              bg=CARD, fg=TEXT, insertbackground=TEXT,
                              relief="flat", highlightthickness=1,
                              highlightbackground=LINE, highlightcolor=ACCENT)
        self.entry.pack(fill="x", pady=(14, 6), ipady=8)
        self.hint = tk.Label(wrap, text="", bg=BG, fg=ERR, font=font(9), anchor="w")
        self.hint.pack(fill="x")

        btns = tk.Frame(wrap, bg=BG)
        btns.pack(fill="x", pady=(12, 0))
        tk.Button(btns, text="取消", command=self._cancel, bg=CARD_LIGHT, fg=TEXT,
                  activebackground=LINE, activeforeground=TEXT, relief="flat",
                  font=font(10), padx=18, pady=6, bd=0).pack(side="right")
        tk.Button(btns, text="确定", command=self._confirm, bg=ACCENT, fg="#ffffff",
                  activebackground="#3d64d6", activeforeground="#ffffff", relief="flat",
                  font=font(10, "bold"), padx=20, pady=6, bd=0).pack(side="right", padx=(0, 10))

        self.entry.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self._cancel())
        self.after(60, self._focus)

    def _focus(self):
        try:
            self.grab_set()
            self.lift()
            self.entry.focus_force()
        except tk.TclError:
            pass

    def _confirm(self):
        self.value = self.entry.get()
        self.destroy()

    def _cancel(self):
        self.value = None
        self.destroy()


def ask_password(parent, settings, title="家长验证", tip="请输入家长密码"):
    """未设置密码时直接放行。返回 (是否通过, 输入内容)。"""
    if not config.has_password(settings):
        return True, ""
    dialog = PasswordDialog(parent, title=title, tip=tip)
    parent.wait_window(dialog)
    value = dialog.value
    if value is None:
        return False, ""
    if config.check_password(settings, value):
        return True, value
    return False, value
