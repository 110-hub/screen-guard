# -*- coding: utf-8 -*-
"""家长端后台管理界面。"""
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk

import config
import ui_common
from ui_common import ACCENT, BG, CARD, CARD_LIGHT, ERR, LINE, MUTED, OK, TEXT, WARN, font

GRADE_TEXT = {g: "小学" for g in range(1, 7)}
GRADE_TEXT.update({7: "七年级", 8: "八年级", 9: "九年级"})
GRADE_TEXT.update({g: "高中" for g in range(10, 13)})


class AdminWindow(tk.Toplevel):
    def __init__(self, controller):
        super().__init__(controller.root)
        self.controller = controller
        self.settings = controller.settings
        self._alive = True

        self.title("屏幕管控后台 · 家长端")
        self.configure(bg=BG)
        self.minsize(900, 640)
        ui_common.center(self, 1000, 760)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ui_common.apply_ttk_style(self)
        self._build_header()
        self._build_tabs()
        self._refresh_status()
        self._tick()

    # ----------------------------- 顶栏 -----------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=BG, padx=24, pady=16)
        header.pack(fill="x")

        tk.Label(header, text="屏幕管控后台", bg=BG, fg=TEXT,
                 font=font(18, "bold")).pack(side="left")
        self.status_label = tk.Label(header, text="", bg=BG, fg=OK, font=font(11, "bold"))
        self.status_label.pack(side="left", padx=(14, 6), pady=(4, 0))
        self.countdown_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=font(11))
        self.countdown_label.pack(side="left", pady=(4, 0))

        btns = tk.Frame(header, bg=BG)
        btns.pack(side="right")
        tk.Button(btns, text="立即弹窗测试", command=self._test_quiz, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=7, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="right", padx=(10, 0))
        self.pause_btn = tk.Button(
            btns, text="暂停 30 分钟", command=self._pause, bg=CARD_LIGHT, fg=TEXT,
            relief="flat", bd=0, font=font(10), padx=14, pady=7, cursor="hand2",
            activebackground=LINE, activeforeground=TEXT)
        self.pause_btn.pack(side="right", padx=(10, 0))
        self.resume_btn = tk.Button(
            btns, text="恢复监控", command=self._resume, bg=ACCENT, fg="#ffffff",
            relief="flat", bd=0, font=font(10, "bold"), padx=14, pady=7, cursor="hand2",
            activebackground="#3d64d6", activeforeground="#ffffff")
        self.resume_btn.pack(side="right")

        line = tk.Frame(self, bg=LINE, height=1)
        line.pack(fill="x", padx=24)

    # ----------------------------- 标签页 -----------------------------
    def _build_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=24, pady=14)

        self.tab_settings = tk.Frame(notebook, bg=BG)
        self.tab_words = tk.Frame(notebook, bg=BG)
        self.tab_wrong = tk.Frame(notebook, bg=BG)
        self.tab_security = tk.Frame(notebook, bg=BG)
        notebook.add(self.tab_settings, text="  管控设置  ")
        notebook.add(self.tab_words, text="  词库  ")
        notebook.add(self.tab_wrong, text="  错词本  ")
        notebook.add(self.tab_security, text="  密码与安全  ")

        self._build_settings_tab()
        self._build_words_tab()
        self._build_wrong_tab()
        self._build_security_tab()

    # ---------- 管控设置 ----------
    def _build_settings_tab(self):
        wrap = tk.Frame(self.tab_settings, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(12, 0))

        card = tk.Frame(wrap, bg=CARD, padx=26, pady=16, highlightthickness=1,
                        highlightbackground=LINE)
        card.pack(fill="x")

        tk.Label(card, text="弹窗节奏", bg=CARD, fg=TEXT, font=font(13, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        s = self.settings
        self.var_interval = tk.IntVar(value=int(s["interval_minutes"]))
        self.var_count = tk.IntVar(value=int(s["words_per_quiz"]))
        self.var_hint = tk.IntVar(value=int(s["hint_after"]))
        self.var_pause = tk.IntVar(value=int(s["pause_minutes_after_skip"]))
        self.var_target = tk.IntVar(value=int(s["daily_target"]))
        self.var_scope = tk.StringVar(value=config.SCOPE_LABELS.get(s["scope"], "全部词库"))
        self.var_enabled = tk.BooleanVar(value=bool(s["enabled"]))
        self.var_allow_skip = tk.BooleanVar(value=bool(s["allow_parent_skip"]))
        self.var_plain = tk.BooleanVar(value=bool(s.get("hint_plaintext", False)))
        self.var_image = tk.BooleanVar(value=bool(s.get("show_image", True)))
        self.var_speak = tk.BooleanVar(value=bool(s.get("speak_word", True)))

        self._row_spin(card, 1, "弹窗周期", self.var_interval, 1, 180, "分钟", "到点自动弹出中文释义，要求输入英文")
        quick = tk.Frame(card, bg=CARD)
        quick.grid(row=1, column=3, sticky="w", padx=(12, 0))
        for minutes in (5, 10, 15, 30):
            tk.Button(quick, text="%d 分" % minutes, command=lambda m=minutes: self.var_interval.set(m),
                      bg=CARD_LIGHT, fg=TEXT, relief="flat", bd=0, font=font(9),
                      padx=8, pady=3, cursor="hand2", activebackground=LINE,
                      activeforeground=TEXT).pack(side="left", padx=(0, 6))

        self._row_spin(card, 2, "每次答题词数", self.var_count, 1, 5, "个", "一次弹窗必须连续答对的单词数量")
        self._row_spin(card, 3, "答错几次给提示", self.var_hint, 0, 5, "次", "答错即提示首字母，达到次数后显示完整字母；0 表示不提示")
        self._row_spin(card, 4, "家长跳过后暂停", self.var_pause, 0, 120, "分钟", "家长密码跳过本次后，暂停管控的时长")
        self._row_spin(card, 5, "每日目标词数", self.var_target, 1, 200, "词", "用于弹窗顶部与统计页的进度展示")

        tk.Label(card, text="出题范围", bg=CARD, fg=TEXT, font=font(10)).grid(
            row=6, column=0, sticky="w", pady=4)
        scope_box = ttk.Combobox(card, textvariable=self.var_scope, state="readonly",
                                 values=list(config.SCOPE_LABELS.values()), width=14,
                                 font=font(10))
        scope_box.grid(row=6, column=1, sticky="w", pady=4)
        self.scope_box = scope_box
        tk.Label(card, text="可按学段（小学/初中/高中）、年级，或只复习错词本", bg=CARD, fg=MUTED,
                 font=font(9)).grid(row=6, column=2, columnspan=2, sticky="w", padx=(12, 0))

        checks = tk.Frame(card, bg=CARD)
        checks.grid(row=7, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Checkbutton(checks, text="启用屏幕管控（关闭后不再自动弹窗）",
                        variable=self.var_enabled).pack(anchor="w")
        ttk.Checkbutton(checks, text="允许家长用密码跳过本次弹窗",
                        variable=self.var_allow_skip).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(checks, text="明文提示单词（答错时直接显示完整拼写）",
                        variable=self.var_plain).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(checks, text="显示单词图片（data/images 下按单词名放图）",
                        variable=self.var_image).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(checks, text="自动朗读单词（使用 Windows 语音）",
                        variable=self.var_speak).pack(anchor="w", pady=(6, 0))

        card.columnconfigure(1, weight=0)

        actions = tk.Frame(wrap, bg=BG)
        actions.pack(fill="x", pady=(18, 0))
        tk.Button(actions, text="保存设置", command=self._save, bg=ACCENT, fg="#ffffff",
                  relief="flat", bd=0, font=font(11, "bold"), padx=28, pady=9,
                  cursor="hand2", activebackground="#3d64d6",
                  activeforeground="#ffffff").pack(side="left")
        tk.Button(actions, text="恢复默认值", command=self._reset_defaults, bg=CARD_LIGHT,
                  fg=TEXT, relief="flat", bd=0, font=font(10), padx=18, pady=9,
                  cursor="hand2", activebackground=LINE, activeforeground=TEXT).pack(
            side="left", padx=(12, 0))
        self.save_tip = tk.Label(actions, text="", bg=BG, fg=OK, font=font(10))
        self.save_tip.pack(side="left", padx=(14, 0))

        # 今日概览卡片
        overview = tk.Frame(wrap, bg=CARD, padx=26, pady=14, highlightthickness=1,
                            highlightbackground=LINE)
        overview.pack(fill="x", pady=(14, 0))
        tk.Label(overview, text="今日概览", bg=CARD, fg=TEXT, font=font(13, "bold")).pack(anchor="w")
        self.overview_label = tk.Label(overview, text="", bg=CARD, fg=MUTED, font=font(11),
                                       justify="left", anchor="w")
        self.overview_label.pack(anchor="w", pady=(8, 4))
        self.week_label = tk.Label(overview, text="", bg=CARD, fg=TEXT, font=font(11),
                                   justify="left", anchor="w")
        self.week_label.pack(anchor="w")

    def _row_spin(self, parent, row, label, variable, low, high, unit, tip):
        tk.Label(parent, text=label, bg=CARD, fg=TEXT, font=font(10)).grid(
            row=row, column=0, sticky="w", pady=4)
        box = tk.Frame(parent, bg=CARD)
        box.grid(row=row, column=1, sticky="w", pady=4)
        spin = tk.Spinbox(box, from_=low, to=high, textvariable=variable, width=5,
                          font=font(10), justify="center", bg=CARD_LIGHT, fg=TEXT,
                          relief="flat", bd=0, insertbackground=TEXT,
                          buttonbackground=CARD_LIGHT, highlightthickness=1,
                          highlightbackground=LINE)
        spin.pack(side="left", ipady=3)
        tk.Label(box, text=unit, bg=CARD, fg=MUTED, font=font(10)).pack(side="left", padx=(6, 0))
        tk.Label(parent, text=tip, bg=CARD, fg=MUTED, font=font(9)).grid(
            row=row, column=2, columnspan=2, sticky="w", padx=(12, 0))
        return spin

    # ---------- 词库 ----------
    def _build_words_tab(self):
        wrap = tk.Frame(self.tab_words, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(12, 0))

        bar = tk.Frame(wrap, bg=BG)
        bar.pack(fill="x")
        self.bank_label = tk.Label(bar, text="", bg=BG, fg=TEXT, font=font(11))
        self.bank_label.pack(side="left")

        tk.Button(bar, text="重新加载词库", command=self._reload_bank, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=6, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="right")

        search_row = tk.Frame(wrap, bg=BG)
        search_row.pack(fill="x", pady=(12, 8))
        self.search_var = tk.StringVar()
        entry = tk.Entry(search_row, textvariable=self.search_var, font=font(10),
                         bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                         highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", lambda e: self._refresh_words())
        tk.Button(search_row, text="搜索", command=self._refresh_words, bg=ACCENT, fg="#ffffff",
                  relief="flat", bd=0, font=font(10, "bold"), padx=18, pady=6,
                  cursor="hand2", activebackground="#3d64d6",
                  activeforeground="#ffffff").pack(side="left", padx=(10, 0))
        tk.Button(search_row, text="显示全部", command=self._clear_search, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=6, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="left", padx=(6, 0))

        table_wrap = tk.Frame(wrap, bg=BG)
        table_wrap.pack(fill="both", expand=True)
        columns = ("word", "pos", "meaning", "grade")
        self.word_tree = ttk.Treeview(table_wrap, columns=columns, show="headings")
        for key, text, width in (("word", "单词", 180), ("pos", "词性", 90),
                                 ("meaning", "中文释义", 480), ("grade", "年级", 90)):
            self.word_tree.heading(key, text=text)
            self.word_tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.word_tree.yview)
        self.word_tree.configure(yscrollcommand=scroll.set)
        self.word_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._refresh_words()

    # ---------- 错词本 ----------
    def _build_wrong_tab(self):
        wrap = tk.Frame(self.tab_wrong, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(12, 0))

        bar = tk.Frame(wrap, bg=BG)
        bar.pack(fill="x")
        self.wrong_label = tk.Label(bar, text="", bg=BG, fg=TEXT, font=font(11))
        self.wrong_label.pack(side="left")
        tk.Button(bar, text="移除选中", command=self._remove_wrong, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=6, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="right", padx=(8, 0))
        tk.Button(bar, text="清空错词本", command=self._clear_wrong, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=6, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="right", padx=(8, 0))
        tk.Button(bar, text="导出为 CSV", command=self._export_wrong, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=6, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="right")

        table_wrap = tk.Frame(wrap, bg=BG)
        table_wrap.pack(fill="both", expand=True, pady=(12, 0))
        columns = ("word", "meaning", "count", "last")
        self.wrong_tree = ttk.Treeview(table_wrap, columns=columns, show="headings")
        for key, text, width in (("word", "单词", 200), ("meaning", "中文释义", 480),
                                 ("count", "错误次数", 110), ("last", "最近一次", 170)):
            self.wrong_tree.heading(key, text=text)
            self.wrong_tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.wrong_tree.yview)
        self.wrong_tree.configure(yscrollcommand=scroll.set)
        self.wrong_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._refresh_wrong()

    # ---------- 密码与安全 ----------
    def _build_security_tab(self):
        wrap = tk.Frame(self.tab_security, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(12, 0))

        card = tk.Frame(wrap, bg=CARD, padx=28, pady=22, highlightthickness=1,
                        highlightbackground=LINE)
        card.pack(fill="x")

        tk.Label(card, text="家长密码", bg=CARD, fg=TEXT, font=font(13, "bold")).pack(anchor="w")
        self.pw_state = tk.Label(card, text="", bg=CARD, fg=WARN, font=font(10))
        self.pw_state.pack(anchor="w", pady=(6, 12))

        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x")
        self.new_pw = tk.Entry(row, show="*", font=font(11), width=24, bg=CARD_LIGHT, fg=TEXT,
                               insertbackground=TEXT, relief="flat", highlightthickness=1,
                               highlightbackground=LINE, highlightcolor=ACCENT)
        self.new_pw.pack(side="left", ipady=6)
        tk.Button(row, text="设置 / 修改密码", command=self._save_password, bg=ACCENT,
                  fg="#ffffff", relief="flat", bd=0, font=font(10, "bold"), padx=18, pady=7,
                  cursor="hand2", activebackground="#3d64d6",
                  activeforeground="#ffffff").pack(side="left", padx=(10, 0))
        tk.Button(row, text="清除密码", command=self._clear_password, bg=CARD_LIGHT, fg=TEXT,
                  relief="flat", bd=0, font=font(10), padx=14, pady=7, cursor="hand2",
                  activebackground=LINE, activeforeground=TEXT).pack(side="left", padx=(8, 0))
        self.pw_tip = tk.Label(card, text="", bg=CARD, font=font(9), fg=MUTED)
        self.pw_tip.pack(anchor="w", pady=(10, 0))

        card2 = tk.Frame(wrap, bg=CARD, padx=28, pady=20, highlightthickness=1,
                         highlightbackground=LINE)
        card2.pack(fill="x", pady=(16, 0))
        tk.Label(card2, text="启动与退出", bg=CARD, fg=TEXT, font=font(13, "bold")).pack(anchor="w")
        self.var_autostart = tk.BooleanVar(value=config.autostart_enabled())
        ttk.Checkbutton(card2, text="开机自动启动屏幕管控", variable=self.var_autostart,
                        command=self._toggle_autostart).pack(anchor="w", pady=(10, 0))
        tk.Label(card2, text="关闭本后台窗口只会隐藏到系统托盘，程序继续常驻管控；"
                             "彻底退出需家长密码。",
                 bg=CARD, fg=MUTED, font=font(9)).pack(anchor="w", pady=(8, 14))
        btns = tk.Frame(card2, bg=CARD)
        btns.pack(anchor="w")
        tk.Button(btns, text="隐藏到托盘", command=lambda: self.controller.hide_admin(),
                  bg=CARD_LIGHT, fg=TEXT, relief="flat", bd=0, font=font(10), padx=20, pady=8,
                  cursor="hand2", activebackground=LINE, activeforeground=TEXT).pack(side="left")
        tk.Button(btns, text="退出屏幕管控", command=self._quit, bg="#3a2030", fg=ERR,
                  relief="flat", bd=0, font=font(10, "bold"), padx=20, pady=8,
                  cursor="hand2", activebackground="#4a2739",
                  activeforeground=ERR).pack(side="left", padx=(10, 0))

        tip = tk.Label(wrap, text="提示：本程序为「中等」管控模式——全屏遮罩 + 窗口置顶，"
                                  "不会拦截系统快捷键；如需强制锁屏请配合家人监督使用。",
                       bg=BG, fg=MUTED, font=font(9), justify="left", wraplength=860)
        tip.pack(anchor="w", pady=(16, 0))
        self._refresh_security()

    # ----------------------------- 状态刷新 -----------------------------
    def _tick(self):
        if not self._alive:
            return
        try:
            self._refresh_status()
        except tk.TclError:
            return
        self.after(1000, self._tick)

    def _refresh_status(self):
        state, text = self.controller.status()
        color = {"running": OK, "paused": WARN, "disabled": MUTED}.get(state, MUTED)
        self.status_label.config(text=text, fg=color)
        self.countdown_label.config(text=self.controller.countdown_text())
        enabled = bool(self.settings.get("enabled"))
        self.pause_btn.config(state="normal" if enabled else "disabled")
        self.resume_btn.config(state="normal" if not enabled else "normal")

        progress = self.controller.progress
        target = max(1, int(self.settings.get("daily_target", 20)))
        streak = sum(1 for _, count in progress.recent_days(7) if count > 0)
        self.overview_label.config(
            text="今日已答对 %d / %d 词 · 累计答题 %d 次 · 正确率 %.1f%% · 错词本 %d 个"
                 % (progress.today_words, target, progress.total_answered,
                    progress.accuracy() * 100, len(progress.wrong)))
        bars = []
        for day, count in progress.recent_days(7):
            label = day[5:]
            mark = "●" if count else "○"
            bars.append("%s %s %2d" % (label, mark, count))
        self.week_label.config(text="最近 7 天： " + "   ".join(bars) + "    （有记录 %d 天）" % streak)

    def _refresh_words(self):
        keyword = self.search_var.get().strip()
        entries = self.controller.bank.search(keyword, limit=400)
        self.word_tree.delete(*self.word_tree.get_children())
        for entry in entries:
            self.word_tree.insert("", "end", values=(
                entry["word"], entry["pos"], entry["meaning"],
                GRADE_TEXT.get(entry["grade"], "-")))
        counts = self.controller.bank.level_counts()
        self.bank_label.config(
            text="词库共 %d 词（小学 %d / 初中 %d / 高中 %d）　%s"
                 % (self.controller.bank.total(), counts["primary"], counts["junior"],
                    counts["senior"], "搜索结果 %d 条" % len(entries) if keyword else ""))

    def _clear_search(self):
        self.search_var.set("")
        self._refresh_words()

    def _reload_bank(self):
        total = self.controller.reload_bank()
        self._refresh_words()
        messagebox.showinfo("词库", "已重新加载词库，共 %d 个单词。" % total, parent=self)

    def _refresh_wrong(self):
        progress = self.controller.progress
        self.wrong_tree.delete(*self.wrong_tree.get_children())
        for word, count, last in progress.wrong_items():
            entry = self.controller.bank.get(word)
            meaning = entry["meaning"] if entry else "—"
            last_text = time.strftime("%m-%d %H:%M", time.localtime(last)) if last else "—"
            self.wrong_tree.insert("", "end", iid=word, values=(word, meaning, count, last_text))
        self.wrong_label.config(text="错词本共 %d 个单词（答对一次错误次数减 1）" % len(progress.wrong))

    def _refresh_security(self):
        if config.has_password(self.settings):
            self.pw_state.config(text="已设置家长密码：修改设置、跳过答题、退出程序都需要验证。", fg=OK)
            self.pw_tip.config(text="留空并点击「设置 / 修改密码」表示不修改。")
        else:
            self.pw_state.config(text="尚未设置密码：任何人都可以进入后台或跳过答题，建议立即设置。", fg=WARN)
            self.pw_tip.config(text="建议设置 4 位以上的家长密码（孩子不知道）。")

    # ----------------------------- 动作 -----------------------------
    def _save(self):
        try:
            interval = max(1, min(180, int(self.var_interval.get())))
            count = max(1, min(5, int(self.var_count.get())))
            hint = max(0, min(5, int(self.var_hint.get())))
            pause = max(0, min(120, int(self.var_pause.get())))
            target = max(1, min(200, int(self.var_target.get())))
        except (tk.TclError, ValueError):
            messagebox.showerror("参数错误", "请输入有效的数字。", parent=self)
            return

        scope = "all"
        for key, label in config.SCOPE_LABELS.items():
            if label == self.var_scope.get():
                scope = key

        self.settings.update({
            "interval_minutes": interval,
            "words_per_quiz": count,
            "hint_after": hint,
            "pause_minutes_after_skip": pause,
            "daily_target": target,
            "scope": scope,
            "enabled": bool(self.var_enabled.get()),
            "allow_parent_skip": bool(self.var_allow_skip.get()),
            "hint_plaintext": bool(self.var_plain.get()),
            "show_image": bool(self.var_image.get()),
            "speak_word": bool(self.var_speak.get()),
        })
        self.controller.apply_settings()
        self.save_tip.config(text="已保存 ✓")
        self.after(1800, lambda: self.save_tip.config(text=""))
        self._refresh_status()
        self._refresh_security()

    def _reset_defaults(self):
        default = config.DEFAULT_SETTINGS
        self.var_interval.set(default["interval_minutes"])
        self.var_count.set(default["words_per_quiz"])
        self.var_hint.set(default["hint_after"])
        self.var_pause.set(default["pause_minutes_after_skip"])
        self.var_target.set(default["daily_target"])
        self.var_scope.set(config.SCOPE_LABELS[default["scope"]])
        self.var_enabled.set(default["enabled"])
        self.var_allow_skip.set(default["allow_parent_skip"])
        self.var_plain.set(default["hint_plaintext"])
        self.var_image.set(default["show_image"])
        self.var_speak.set(default["speak_word"])

    def _test_quiz(self):
        self.controller.trigger_quiz(manual=True)

    def _pause(self):
        self.controller.pause_minutes(30)
        self._refresh_status()

    def _resume(self):
        self.controller.resume()
        self._refresh_status()

    def _save_password(self):
        password = self.new_pw.get().strip()
        if not password:
            self.pw_tip.config(text="密码不能为空；如要取消密码请点「清除密码」。", fg=ERR)
            return
        if len(password) < 4:
            self.pw_tip.config(text="密码太短，建议至少 4 位。", fg=ERR)
            return
        config.set_password(self.settings, password)
        self.new_pw.delete(0, "end")
        self.pw_tip.config(text="密码已更新 ✓", fg=OK)
        self._refresh_security()

    def _clear_password(self):
        ok, _ = ui_common.ask_password(self, self.settings, tip="验证后清除家长密码")
        if not ok:
            return
        config.set_password(self.settings, "")
        self.pw_tip.config(text="已清除密码，后台不再受保护。", fg=WARN)
        self._refresh_security()

    def _toggle_autostart(self):
        enable = bool(self.var_autostart.get())
        if not config.apply_autostart(enable):
            messagebox.showwarning("开机自启", "写入启动项失败，请检查系统权限。", parent=self)
            self.var_autostart.set(config.autostart_enabled())
            return
        self.settings["autostart"] = enable
        config.save_settings(self.settings)

    def _remove_wrong(self):
        for item in self.wrong_tree.selection():
            self.controller.progress.remove_wrong(item)
        self._refresh_wrong()
        self._refresh_status()

    def _clear_wrong(self):
        if not messagebox.askyesno("清空错词本", "确定清空全部错词记录吗？", parent=self):
            return
        self.controller.progress.clear_wrong()
        self._refresh_wrong()
        self._refresh_status()

    def _export_wrong(self):
        import csv
        path = time.strftime("错词本_%Y%m%d_%H%M.csv")
        path = os.path.join(config.DATA_DIR, path)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["单词", "词性", "中文释义", "错误次数", "最近一次"])
            for word, count, last in self.controller.progress.wrong_items():
                entry = self.controller.bank.get(word) or {"pos": "", "meaning": ""}
                writer.writerow([word, entry["pos"], entry["meaning"], count,
                                 time.strftime("%Y-%m-%d %H:%M", time.localtime(last)) if last else ""])
        messagebox.showinfo("导出成功", "错词本已导出到：\n" + path, parent=self)

    def _quit(self):
        self.controller.request_quit()

    def _on_close(self):
        tray = getattr(self.controller, "tray", None)
        if tray is not None and getattr(tray, "icon", None) is not None:
            self.controller.hide_admin()
        else:
            self._quit()

    def close(self):
        self._alive = False
        try:
            self.destroy()
        except tk.TclError:
            pass
