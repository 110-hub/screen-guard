# -*- coding: utf-8 -*-
"""系统托盘常驻图标（依赖 pystray + Pillow；缺失时自动降级为任务栏模式）。"""
import threading

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    HAS_TRAY = True
except Exception:      # 依赖缺失或平台不支持
    HAS_TRAY = False


def _make_image():
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([2, 2, size - 3, size - 3], radius=14, fill=(79, 124, 255, 255))
    font = None
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, 42)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((size / 2, size / 2 - 2), "A", font=font, fill=(255, 255, 255, 255), anchor="mm")
    return image


class Tray:
    """托盘图标：常驻后台，右键菜单可打开后台、暂停、退出。"""

    def __init__(self, controller):
        self.controller = controller
        self.icon = None
        self.thread = None

    def start(self):
        if not HAS_TRAY:
            return False
        menu = pystray.Menu(
            pystray.MenuItem("打开后台", self._open, default=True),
            pystray.MenuItem("立即弹窗测试", self._test),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("暂停 30 分钟", self._pause),
            pystray.MenuItem("恢复监控", self._resume),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出（需密码）", self._quit),
        )
        self.icon = pystray.Icon("ScreenGuard", _make_image(),
                                 "屏幕管控 · 英语单词", menu)
        self.thread = threading.Thread(target=self.icon.run, name="tray", daemon=True)
        self.thread.start()
        return True

    # pystray 的回调跑在托盘线程里，统一切回 Tk 主线程执行
    def _call(self, func):
        try:
            self.controller.root.after(0, func)
        except Exception:
            pass

    def _open(self, icon=None, item=None):
        self._call(self.controller.show_admin)

    def _test(self, icon=None, item=None):
        self._call(lambda: self.controller.trigger_quiz(manual=True))

    def _pause(self, icon=None, item=None):
        self._call(lambda: self.controller.pause_minutes(30))

    def _resume(self, icon=None, item=None):
        self._call(self.controller.resume)

    def _quit(self, icon=None, item=None):
        self._call(self.controller.request_quit)

    def notify(self, message, title="屏幕管控"):
        if not self.icon:
            return
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def update_title(self, text):
        if not self.icon:
            return
        try:
            self.icon.title = text
        except Exception:
            pass

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
