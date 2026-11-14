# -*- coding: utf-8 -*-
"""配置、密码与开机自启管理。"""
import hashlib
import json
import os
import secrets
import shutil
import sys

# 打包成 exe 后，程序文件在安装目录，内置资源在 _internal（sys._MEIPASS）
FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable)) if FROZEN \
    else os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
APP_NAME = "ScreenGuard"

DATA_DIR = os.path.join(BASE_DIR, "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "progress.json")
WORDS_DIR = os.path.join(DATA_DIR, "words")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
VOICE_DIR = os.path.join(DATA_DIR, "voice")
BUNDLED_WORDS_DIR = os.path.join(BUNDLE_DIR, "data", "words")

DEFAULT_SETTINGS = {
    "enabled": True,              # 管控总开关
    "interval_minutes": 10,       # 弹窗周期（分钟）
    "words_per_quiz": 1,          # 每次弹窗需要答对的词数
    "scope": "all",               # 出题范围：all / grade7 / grade8 / grade9 / wrong
    "hint_after": 2,              # 答错几次后显示字母提示
    "hint_plaintext": False,      # 答错时直接显示完整单词（明文提示）
    "show_image": True,           # 弹窗中显示单词图片
    "speak_word": True,           # 弹窗时自动朗读单词
    "allow_parent_skip": True,    # 允许家长密码跳过本次弹窗
    "pause_minutes_after_skip": 15,  # 家长跳过后暂停管控的分钟数
    "daily_target": 20,           # 每日目标词数（进度条）
    "password": "",               # salt:sha256，空表示未设置密码
    "autostart": False,           # 开机自启
}

SCOPE_LABELS = {
    "all": "全部词库",
    "primary": "小学",
    "junior": "初中",
    "grade7": "七年级",
    "grade8": "八年级",
    "grade9": "九年级",
    "senior": "高中",
    "wrong": "仅错词本",
}
SCOPE_GRADE = {"grade7": 7, "grade8": 8, "grade9": 9}
SCOPE_GRADES = {"primary": (1, 2, 3, 4, 5, 6), "junior": (7, 8, 9), "senior": (10, 11, 12)}

LEVEL_LABELS = {"primary": "小学", "junior": "初中", "senior": "高中"}

AUTOSTART_NAME = "屏幕管控.bat"


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(WORDS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(VOICE_DIR, exist_ok=True)


def seed_words():
    """把内置词库释放到 data/words：缺哪个补哪个，已有文件不覆盖。"""
    ensure_dirs()
    if not os.path.isdir(BUNDLED_WORDS_DIR):
        return
    for name in os.listdir(BUNDLED_WORDS_DIR):
        if not name.endswith(".txt"):
            continue
        target = os.path.join(WORDS_DIR, name)
        if os.path.exists(target):
            continue
        try:
            shutil.copy2(os.path.join(BUNDLED_WORDS_DIR, name), target)
        except OSError:
            pass


def load_settings():
    ensure_dirs()
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for key, value in saved.items():
                    if key in DEFAULT_SETTINGS:
                        settings[key] = value
        except (OSError, ValueError):
            pass
    return settings


def save_settings(settings):
    ensure_dirs()
    tmp_path = SETTINGS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, SETTINGS_PATH)


def write_json_atomic(path, data):
    ensure_dirs()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


# ----------------------------- 密码 -----------------------------

def _digest(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def set_password(settings, password):
    """password 为空字符串表示清除密码。"""
    password = (password or "").strip()
    if not password:
        settings["password"] = ""
    else:
        salt = secrets.token_hex(8)
        settings["password"] = "%s:%s" % (salt, _digest(password, salt))
    save_settings(settings)


def check_password(settings, password):
    """未设置密码时始终返回 True（首次使用时允许自由进入后台）。"""
    stored = settings.get("password") or ""
    if not stored:
        return True
    if ":" not in stored:
        return False
    salt, digest = stored.split(":", 1)
    return secrets.compare_digest(digest, _digest((password or "").strip(), salt))


def has_password(settings):
    return bool(settings.get("password"))


# ----------------------------- 开机自启 -----------------------------

def _startup_dir():
    return os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
    )


def autostart_enabled():
    return os.path.exists(os.path.join(_startup_dir(), AUTOSTART_NAME))


def apply_autostart(enable):
    """在系统启动文件夹写入/删除启动脚本，返回是否成功。"""
    path = os.path.join(_startup_dir(), AUTOSTART_NAME)
    try:
        if enable:
            if FROZEN:
                target = '"%s"' % sys.executable
            else:
                python = sys.executable or "python"
                pythonw = python.replace("python.exe", "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = python
                target = '"%s" "%s"' % (pythonw, os.path.join(BASE_DIR, "main.py"))
            content = '@echo off\r\nstart "" %s --silent\r\n' % target
            with open(path, "w", encoding="gbk") as f:
                f.write(content)
        elif os.path.exists(path):
            os.remove(path)
        return True
    except OSError:
        return False
