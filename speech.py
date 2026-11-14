# -*- coding: utf-8 -*-
"""单词发音：用 Windows 自带 SAPI 合成 wav 并缓存，播放不阻塞界面。"""
import os
import subprocess
import sys
import threading

import config

try:
    import winsound
except ImportError:          # 非 Windows
    winsound = None

_lock = threading.Lock()
_busy = set()


def available():
    return sys.platform == "win32" and winsound is not None


def _cache_path(word):
    name = "".join(ch if ch.isalnum() else "_" for ch in word.lower())
    return os.path.join(config.VOICE_DIR, name + ".wav")


def _synthesize(word, path):
    """调用 PowerShell 的 System.Speech 合成英文语音；优先选英文发音人。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v=$s.GetInstalledVoices()|Where-Object{$_.VoiceInfo.Culture.Name -like 'en*'}|"
        "Select-Object -First 1;"
        "if($v){$s.SelectVoice($v.VoiceInfo.Name)};"
        "$s.Rate=-1;"
        "$s.SetOutputToWaveFile('%s');"
        "$s.Speak('%s');"
        "$s.Dispose()" % (path.replace("'", "''"), word.replace("'", "''"))
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, timeout=30, creationflags=0x08000000,
    )


def _play(word):
    try:
        path = _cache_path(word)
        if not os.path.exists(path):
            os.makedirs(config.VOICE_DIR, exist_ok=True)
            _synthesize(word, path)
        if os.path.exists(path):
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        with _lock:
            _busy.discard(word)


def speak(word):
    """后台朗读单词；同一单词正在合成时不重复触发。"""
    word = (word or "").strip()
    if not word or not available():
        return
    with _lock:
        if word in _busy:
            return
        _busy.add(word)
    threading.Thread(target=_play, args=(word,), daemon=True).start()
