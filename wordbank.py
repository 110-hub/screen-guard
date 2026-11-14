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
        seen = set()
        config.ensure_dirs()
        files = sorted(glob.glob(os.path.join(self.words_dir, "*.txt")))
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    entry = self._parse(raw)
                    if not entry:
                        continue
                    key = (entry["word"], entry["grade"])
                    if key in seen:
                        continue
                    # 同一单词可以同时属于多个学段；查词含义时取年级最低的那条
                    seen.add(key)
                    self.entries.append(entry)
                    old = self.words.get(entry["word"])
                    if old is None or entry["grade"] < old["grade"]:
                        self.words[entry["word"]] = entry
        return len(self.words)

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
        if grade not in range(1, 13):
            grade = 8
        return {"word": word, "pos": pos, "meaning": meaning, "grade": grade}

    # ----------------------------- 查询 -----------------------------
    def total(self):
        return len(self.words)

    def grade_counts(self):
        counts = {g: 0 for g in range(1, 13)}
        for entry in self.entries:
            counts[entry["grade"]] = counts.get(entry["grade"], 0) + 1
        return counts

    def level_counts(self):
        counts = self.grade_counts()
        return {
            "primary": sum(counts.get(g, 0) for g in range(1, 7)),
            "junior": sum(counts.get(g, 0) for g in range(7, 10)),
            "senior": sum(counts.get(g, 0) for g in range(10, 13)),
        }

    def get(self, word):
        return self.words.get((word or "").lower())

    def _in_scope(self, scope):
        grade = config.SCOPE_GRADE.get(scope)
        if grade is not None:
            return [e for e in self.entries if e["grade"] == grade]
        grades = config.SCOPE_GRADES.get(scope)
        if grades:
            return [e for e in self.entries if e["grade"] in grades]
        return self.entries

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
            matched = self.entries
        else:
            matched = [e for e in self.entries
                       if keyword in e["word"] or keyword in e["meaning"]]
        result, seen = [], set()
        for entry in matched:
            word = entry["word"]
            if word in seen:
                continue
            seen.add(word)
            result.append(self.words.get(word, entry))
            if len(result) >= limit:
                break
        return result
