# -*- coding: utf-8 -*-
"""全屏答题遮罩：显示中文释义，必须输入正确英文才能关闭。"""
import time
import tkinter as tk

import ui_common
from ui_common import font, ACCENT, BG, CARD, CARD_LIGHT, ERR, LINE, MUTED, OK, TEXT, WARN


def _monitor_rects():
    """枚举所有显示器的矩形（Windows）。失败时返回空列表。"""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        rects = []

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.POINTER(wintypes.RECT), ctypes.c_ssize_t,
        )

        def _callback(hmonitor, hdc, lprect, lparam):
            rect = lprect.contents
            rects.append((rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
            return 1

        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_callback), 0)
        return rects
    except Exception:
        return []


def normalize(answer):
    return " ".join((answer or "").lower().replace("’", "'").split())


def common_prefix(answer, word):
    """已拼对的开头字母数（忽略大小写与多余空格）。"""
    a, w = normalize(answer), normalize(word)
    n = 0
    for x, y in zip(a, w):
        if x != y:
            break
        n += 1
    return n


def mask_of(word):
    """生成字母提示：首字母 + 下划线。"""
    chunks = []
    for part in word.split(" "):
        if len(part) <= 1:
            chunks.append(part)
        else:
            chunks.append(part[0] + " " + " ".join("_" for _ in part[1:]))
    return "   /   ".join(chunks)


class QuizOverlay(tk.Toplevel):
    """一次弹窗可能需要连续答对 words 里的所有单词。"""

    def __init__(self, master, controller, words):
        super().__init__(master)
        self.controller = controller
        self.settings = controller.settings
        self.words_picked = words
        self.index = 0
        self.attempts = 0
        self.fail_recorded = False
        self.started_at = time.time()
        self.closed = False
        self.blind_windows = []

        self.configure(bg=BG)
        self.title("单词闯关")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind("<Escape>", lambda e: "break")
        self.bind("<Alt-F4>", lambda e: "break")

        self._build()
        self._cover_other_monitors()
        self._render_word()
        self.after(60, self._focus_entry)
        self._tick_elapsed()

    # ----------------------------- 界面 -----------------------------
    def _build(self):
        header = tk.Frame(self, bg=BG, padx=48, pady=24)
        header.pack(fill="x")
        tk.Label(header, text="单词闯关", bg=BG, fg=TEXT, font=font(20, "bold"),
                 anchor="w").pack(side="left")
        tk.Label(header, text="  输入正确英文后即可继续使用电脑", bg=BG, fg=MUTED,
                 font=font(11)).pack(side="left", padx=(8, 0))

        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self.elapsed_label = tk.Label(right, text="00:00", bg=BG, fg=MUTED, font=font(11))
        self.elapsed_label.pack(side="right", padx=(12, 0))
        target = max(1, int(self.settings.get("daily_target", 20)))
        today = self.controller.progress.today_words
        self.progress_label = tk.Label(
            right, text="今日 %d / %d 词" % (today, target), bg=BG, fg=MUTED, font=font(11))
        self.progress_label.pack(side="right", padx=(0, 6))
        self.progress_bar = tk.Frame(right, bg=CARD_LIGHT, height=8, width=160)
        self.progress_bar.pack(side="right", padx=(0, 8))
        self.progress_bar.pack_propagate(False)
        ratio = min(1.0, today / float(target))
        if ratio > 0:
            tk.Frame(self.progress_bar, bg=ACCENT, height=8).place(
                relx=0, rely=0, relwidth=ratio, relheight=1)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=48, pady=(8, 0))

        self.card = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.card.pack(expand=True)

        inner = tk.Frame(self.card, bg=CARD)
        inner.pack(padx=56, pady=36)
        tk.Frame(inner, bg=CARD, width=780, height=1).pack()   # 固定卡片宽度

        self.index_label = tk.Label(inner, text="", bg=CARD, fg=MUTED, font=font(11))
        self.index_label.pack(anchor="w")

        self.pos_label = tk.Label(inner, text="", bg=CARD, fg=WARN, font=font(14, "bold"))
        self.pos_label.pack(pady=(22, 4))

        self.meaning_label = tk.Label(inner, text="", bg=CARD, fg=TEXT,
                                      font=font(38, "bold"), wraplength=760, justify="center")
        self.meaning_label.pack(pady=(0, 6))

        tk.Label(inner, text="请拼写出对应的英文单词", bg=CARD, fg=MUTED,
                 font=font(11)).pack(pady=(8, 16))

        entry_row = tk.Frame(inner, bg=CARD)
        entry_row.pack()
        self.entry = tk.Entry(entry_row, font=font(30, "normal", "Segoe UI"), justify="center",
                              width=24, bg=CARD_LIGHT, fg=TEXT, insertbackground=ACCENT,
                              disabledbackground=CARD_LIGHT, disabledforeground=OK,
                              relief="flat", highlightthickness=2,
                              highlightbackground=LINE, highlightcolor=ACCENT)
        self.entry.pack(ipady=10)
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<KP_Enter>", self._submit)

        self.hint_label = tk.Label(inner, text="", bg=CARD, fg=MUTED, font=font(13))
        self.hint_label.pack(pady=(14, 0))

        self.feedback_label = tk.Label(inner, text="", bg=CARD, fg=ERR, font=font(13, "bold"))
        self.feedback_label.pack(pady=(4, 0))

        self.submit_btn = tk.Button(
            inner, text="提交答案  ( Enter )", command=self._submit,
            bg=ACCENT, fg="#ffffff", activebackground="#3d64d6", activeforeground="#ffffff",
            relief="flat", bd=0, font=font(13, "bold"), padx=44, pady=12, cursor="hand2")
        self.submit_btn.pack(pady=(18, 0))

        footer = tk.Frame(self, bg=BG, padx=48, pady=20)
        footer.pack(fill="x")
        self.stat_label = tk.Label(footer, text="", bg=BG, fg=MUTED, font=font(10), anchor="w")
        self.stat_label.pack(side="left")
        if self.settings.get("allow_parent_skip", True):
            tk.Button(footer, text="家长解锁跳过（需密码）", command=self._parent_skip,
                      bg=BG, fg=MUTED, activebackground=CARD, activeforeground=TEXT,
                      relief="flat", bd=0, font=font(10), cursor="hand2").pack(side="right")

    def _render_word(self):
        if self.index >= len(self.words_picked):
            return
        entry = self.words_picked[self.index]
        self.attempts = 0
        self.fail_recorded = False
        total = len(self.words_picked)
        self.index_label.config(
            text=("第 %d / %d 题" % (self.index + 1, total)) if total > 1 else "本次练习")
        self.pos_label.config(text=entry["pos"])
        self.meaning_label.config(text=entry["meaning"])
        self.hint_label.config(text="")
        self.feedback_label.config(text="")
        self.entry.config(state="normal", highlightbackground=LINE)
        self.entry.delete(0, "end")
        self._update_stat()
        self.after(40, self._focus_entry)

    def _update_stat(self):
        progress = self.controller.progress
        acc = progress.accuracy() * 100
        self.stat_label.config(
            text="累计答题 %d 次 · 正确率 %.1f%% · 错词 %d 个 · 本次错 %d 次"
                 % (progress.total_answered, acc, len(progress.wrong), self.attempts))

    def _tick_elapsed(self):
        if self.closed:
            return
        passed = int(time.time() - self.started_at)
        self.elapsed_label.config(text="%02d:%02d" % (passed // 60, passed % 60))
        self.after(1000, self._tick_elapsed)

    # ----------------------------- 焦点 / 多屏 -----------------------------
    def _focus_entry(self):
        if self.closed:
            return
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            if self.entry.cget("state") != "disabled":
                self.entry.focus_force()
        except tk.TclError:
            pass

    def _cover_other_monitors(self):
        """多显示器时，用不接收输入的黑屏遮住其它屏幕。"""
        rects = _monitor_rects()
        if len(rects) <= 1:
            return
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        for (x, y, w, h) in rects:
            if x == 0 and y == 0 and w == screen_w and h == screen_h:
                continue
            try:
                win = tk.Toplevel(self)
                win.overrideredirect(True)
                win.geometry("%dx%d+%d+%d" % (w, h, x, y))
                win.configure(bg=BG)
                win.attributes("-topmost", True)
                tk.Label(win, text="请在主屏幕完成单词闯关", bg=BG, fg=MUTED,
                         font=font(26, "bold")).place(relx=0.5, rely=0.5, anchor="center")
                self.blind_windows.append(win)
            except tk.TclError:
                pass

    # ----------------------------- 逻辑 -----------------------------
    def _submit(self, event=None):
        if self.closed or self.index >= len(self.words_picked):
            return "break"
        if self.entry.cget("state") == "disabled":
            return "break"
        answer = self.entry.get().strip()
        if not answer:
            self._flash("请先输入英文单词", ERR)
            return "break"
        current = self.words_picked[self.index]
        if normalize(answer) == normalize(current["word"]):
            self._on_correct(current)
        else:
            self._on_wrong(current, answer)
        return "break"

    def _on_correct(self, entry):
        self.controller.progress.record_pass(entry["word"])
        self.entry.config(state="disabled", highlightbackground=OK, highlightcolor=OK)
        self.feedback_label.config(text="✔ 正确：" + entry["word"], fg=OK)
        self.hint_label.config(text=entry["word"] + "  " + entry["pos"] + "  " + entry["meaning"],
                               fg=MUTED)
        self.progress_label.config(
            text="今日 %d / %d 词" % (self.controller.progress.today_words,
                                    max(1, int(self.settings.get("daily_target", 20))))
        )
        self._update_stat()
        self.index += 1
        self.after(800, self._advance)

    def _advance(self):
        if self.closed:
            return
        if self.index >= len(self.words_picked):
            self._finish()
        else:
            self._render_word()

    def _on_wrong(self, entry, answer):
        self.attempts += 1
        if not self.fail_recorded:
            self.controller.progress.record_fail(entry["word"])
            self.fail_recorded = True
        else:
            self.controller.progress.save()
        self._flash("✘ “%s” 不是正确答案，再试一次" % answer, ERR)
        hint_after = int(self.settings.get("hint_after", 2))
        if hint_after > 0:
            self._show_hint(entry["word"], answer, self.attempts >= hint_after)
        self.entry.delete(0, "end")
        self._update_stat()

    def _show_hint(self, word, answer, full):
        """答错后立即提示：先给首字母/已拼对部分，达到次数后给完整字母提示。"""
        letters = len(word.replace(" ", ""))
        if full:
            text = "提示：%s   （共 %d 个字母）" % (mask_of(word), letters)
        else:
            matched = common_prefix(answer, word)
            if matched:
                text = "提示：开头 “%s” 已拼对，共 %d 个字母，注意后面的部分" % (
                    normalize(word)[:matched], letters)
            else:
                text = "提示：首字母是“%s”，共 %d 个字母" % (word[0], letters)
        self.hint_label.config(text=text, fg=WARN)

    def _flash(self, text, color):
        self.feedback_label.config(text=text, fg=color)
        self.entry.config(highlightbackground=color, highlightcolor=color)
        self.after(1400, lambda: self._reset_highlight())

    def _reset_highlight(self):
        if self.closed or self.entry.cget("state") == "disabled":
            return
        self.entry.config(highlightbackground=LINE, highlightcolor=ACCENT)

    def _parent_skip(self):
        ok, _ = ui_common.ask_password(self, self.settings, tip="输入家长密码可跳过本次答题")
        if not ok:
            self._flash("密码不正确，不能跳过", ERR)
            return
        if self.index < len(self.words_picked):
            self.controller.progress.record_skip(self.words_picked[self.index]["word"])
        pause = int(self.settings.get("pause_minutes_after_skip", 15))
        self.controller.on_quiz_skipped(self, pause)
        self._close()

    def _finish(self):
        self.controller.on_quiz_finished(self)
        self._close()

    def _close(self):
        if self.closed:
            return
        self.closed = True
        for win in self.blind_windows:
            try:
                win.destroy()
            except tk.TclError:
                pass
        self.blind_windows = []
        try:
            self.destroy()
        except tk.TclError:
            pass
