# -*- coding: utf-8 -*-
"""词库加载与抽题逻辑。

词库文件格式（data/words/words_*.txt，每行一条）：
    word|pos|含义|grade
"""
import glob
import os
import random

import config

VALID_POS = {"n.", "v.", "adj.", "adv.", "pron.", "prep.", "conj.", "num.",
             "art.", "modal", "phr.", "int."}


class WordBank:
    def __init__(self, words_dir=None):
        self.words_dir = words_dir or config.WORDS_DIR
        self.entries = []
        self.words = {}

    # ----------------------------- 加载 -----------------------------
    def load(self):
        self.entries = []
        self.words = {}
        config.ensure_dirs()
        files = sorted(glob.glob(os.path.join(self.words_dir, "*.txt")))
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    entry = self._parse(raw)
                    if entry and entry["word"] not in self.words:
                        self.words[entry["word"]] = entry
                        self.entries.append(entry)
        return len(self.entries)

    def _parse(self, raw):
        line = raw.strip()
        if not line or line.startswith("#"):
            return None
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            return None
        word = parts[0].lower()
        if not word or not word.replace(" ", "").replace("-", "").replace("'", "").isalpha():
            return None
        pos = parts[1] if parts[1] in VALID_POS else (parts[1] or "n.")
        meaning = parts[2]
        if not meaning:
            return None
        try:
            grade = int(parts[3]) if len(parts) > 3 else 8
        except ValueError:
            grade = 8
        if grade not in (7, 8, 9):
            grade = 8
        return {"word": word, "pos": pos, "meaning": meaning, "grade": grade}

    # ----------------------------- 查询 -----------------------------
    def total(self):
        return len(self.entries)

    def grade_counts(self):
        counts = {7: 0, 8: 0, 9: 0}
        for entry in self.entries:
            counts[entry["grade"]] = counts.get(entry["grade"], 0) + 1
        return counts

    def get(self, word):
        return self.words.get((word or "").lower())

    def _in_scope(self, scope):
        grade = config.SCOPE_GRADE.get(scope)
        if grade is None:
            return self.entries
        return [e for e in self.entries if e["grade"] == grade]

    # ----------------------------- 抽题 -----------------------------
    def pick(self, scope="all", progress=None, count=1):
        """按范围抽 count 个不重复的单词，尽量避开最近出现过的词。"""
        wrong_words = list(progress.wrong.keys()) if progress else []
        pool = self._in_scope(scope)

        if scope == "wrong":
            pool = [e for e in pool if e["word"] in wrong_words]

        if not pool:
            pool = self._in_scope("all") or list(self.entries)
        if not pool:
            return []

        recent = set(progress.recent[-20:]) if progress else set()
        fresh = [e for e in pool if e["word"] not in recent] or pool

        picked = []
        used = set()
        for _ in range(count):
            candidates = [e for e in fresh if e["word"] not in used]
            if not candidates:
                candidates = [e for e in pool if e["word"] not in used]
            if not candidates:
                break
            # 全部范围时，有错词的场合给小比例优先权，强化薄弱词
            if scope == "all" and wrong_words and random.random() < 0.25:
                weak = [e for e in candidates if e["word"] in wrong_words]
                if weak:
                    candidates = weak
            entry = random.choice(candidates)
            used.add(entry["word"])
            picked.append(entry)
        return picked

    def search(self, keyword, limit=200):
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return self.entries[:limit]
        return [e for e in self.entries
                if keyword in e["word"] or keyword in e["meaning"]][:limit]
