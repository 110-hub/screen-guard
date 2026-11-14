# -*- coding: utf-8 -*-
"""答题进度、错词本与统计数据的持久化。"""
import datetime
import time

import config

RECENT_LIMIT = 40      # 记住最近出现的词，避免短时间重复出题
DAILY_KEEP_DAYS = 14   # 保留最近多少天的记录


def _today():
    return datetime.date.today().isoformat()


class Progress:
    def __init__(self, path=None):
        self.path = path or config.PROGRESS_PATH
        data = config.read_json(self.path, {})
        stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
        self.total_answered = int(stats.get("total_answered", 0))
        self.total_passed = int(stats.get("total_passed", 0))
        self.total_failed = int(stats.get("total_failed", 0))
        self.total_skipped = int(stats.get("total_skipped", 0))
        self.today_date = stats.get("today_date") or _today()
        self.today_words = int(stats.get("today_words", 0)) if self.today_date == _today() else 0
        self.wrong = data.get("wrong") if isinstance(data.get("wrong"), dict) else {}
        self.recent = data.get("recent") if isinstance(data.get("recent"), list) else []
        self.daily = data.get("daily") if isinstance(data.get("daily"), dict) else {}
        self._roll_date()

    # ----------------------------- 内部 -----------------------------
    def _roll_date(self):
        """跨天时把当日计数清零。"""
        today = _today()
        if self.today_date != today:
            self.today_date = today
            self.today_words = 0

    def save(self):
        self._roll_date()
        self.daily[self.today_date] = self.today_words
        # 只保留最近若干天
        if len(self.daily) > DAILY_KEEP_DAYS:
            keep = sorted(self.daily.keys())[-DAILY_KEEP_DAYS:]
            self.daily = {k: self.daily[k] for k in keep}
        config.write_json_atomic(self.path, {
            "stats": {
                "total_answered": self.total_answered,
                "total_passed": self.total_passed,
                "total_failed": self.total_failed,
                "total_skipped": self.total_skipped,
                "today_date": self.today_date,
                "today_words": self.today_words,
            },
            "wrong": self.wrong,
            "recent": self.recent[-RECENT_LIMIT:],
            "daily": self.daily,
        })

    def _remember(self, word):
        self.recent.append(word)
        self.recent = self.recent[-RECENT_LIMIT:]

    # ----------------------------- 记录 -----------------------------
    def record_pass(self, word):
        self._roll_date()
        self.total_answered += 1
        self.total_passed += 1
        self.today_words += 1
        # 答对后从错词本里减少一次错误次数
        if word in self.wrong:
            left = int(self.wrong[word].get("count", 0)) - 1
            if left <= 0:
                self.wrong.pop(word, None)
            else:
                self.wrong[word]["count"] = left
                self.wrong[word]["last"] = time.time()
        self._remember(word)
        self.save()

    def record_fail(self, word):
        self._roll_date()
        self.total_answered += 1
        self.total_failed += 1
        item = self.wrong.get(word) or {"count": 0, "last": 0}
        item["count"] = int(item.get("count", 0)) + 1
        item["last"] = time.time()
        self.wrong[word] = item
        self._remember(word)
        self.save()

    def record_skip(self, word):
        self._roll_date()
        self.total_skipped += 1
        item = self.wrong.get(word) or {"count": 0, "last": 0}
        item["count"] = int(item.get("count", 0)) + 2   # 跳过等同于没掌握
        item["last"] = time.time()
        self.wrong[word] = item
        self._remember(word)
        self.save()

    # ----------------------------- 查询 -----------------------------
    def accuracy(self):
        if not self.total_answered:
            return 0.0
        return self.total_passed / float(self.total_answered)

    def wrong_items(self):
        """按错误次数从多到少返回 [(word, count, last_ts), ...]。"""
        items = [(w, int(v.get("count", 0)), float(v.get("last", 0)))
                 for w, v in self.wrong.items() if isinstance(v, dict)]
        items.sort(key=lambda x: (-x[1], -x[2]))
        return items

    def remove_wrong(self, word):
        self.wrong.pop(word, None)
        self.save()

    def clear_wrong(self):
        self.wrong = {}
        self.save()

    def recent_days(self, days=7):
        """返回 [(日期, 词数), ...]，用于趋势展示。"""
        today = datetime.date.today()
        out = []
        for i in range(days - 1, -1, -1):
            day = (today - datetime.timedelta(days=i)).isoformat()
            if i == 0:
                out.append((day, self.today_words))
            else:
                out.append((day, int(self.daily.get(day, 0))))
        return out
