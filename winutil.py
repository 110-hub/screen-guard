# -*- coding: utf-8 -*-
"""Windows 系统操作：快捷方式、开机自启、卸载注册表、结束进程、自删除。

统一用 PowerShell(EncodedCommand) 创建 .lnk，避免中文路径与引号转义问题；
已知文件夹用 SHGetKnownFolderPath 读取（支持桌面/文档被 OneDrive 重定向的情况）。
"""
import base64
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import tempfile
import winreg

APP_NAME = "屏幕管控"
EXE_NAME = "ScreenGuard.exe"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ScreenGuard"
CREATE_NO_WINDOW = 0x08000000

# FOLDERID
_FOLDER_IDS = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "startup": "{B97D20BB-F46A-4C97-BA10-5E3608430854}",
    "programs": "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}",
}


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


def known_folder(kind):
    """返回「桌面 / 启动 / 开始菜单程序」目录的绝对路径。"""
    raw = _FOLDER_IDS[kind].strip("{}")
    parts = raw.split("-")            # 8-4-4-4-12
    guid = _GUID(int(parts[0], 16), int(parts[1], 16), int(parts[2], 16),
                 (ctypes.c_ubyte * 8)(*[int((parts[3] + parts[4])[i:i + 2], 16)
                                       for i in range(0, 16, 2)]))
    path_ptr = ctypes.c_wchar_p()
    ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                               ctypes.byref(path_ptr))
    path = path_ptr.value or ""
    ctypes.windll.ole32.CoTaskMemFree(path_ptr)
    if path:
        return path
    # 极端情况下回退
    fallback = {"desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
                "startup": os.path.join(os.environ.get("APPDATA", ""),
                                        r"Microsoft\Windows\Start Menu\Programs\Startup"),
                "programs": os.path.join(os.environ.get("APPDATA", ""),
                                         r"Microsoft\Windows\Start Menu\Programs")}[kind]
    return fallback


def _run_ps(script, timeout=40):
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
                       timeout=timeout, creationflags=CREATE_NO_WINDOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def create_shortcut(link_path, target, arguments="", description="", icon=None):
    icon = icon or target
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        "$s.TargetPath='{target}';$s.WorkingDirectory='{work}';"
        "$s.Arguments='{args}';$s.Description='{desc}';"
        "$s.IconLocation='{icon},0';$s.Save()"
    ).format(link=link_path, target=target, work=os.path.dirname(target),
             args=arguments, desc=description, icon=icon)
    return _run_ps(script)


def shortcut_paths():
    """返回需要维护的快捷方式：(桌面, 开始菜单, 启动)。"""
    return (os.path.join(known_folder("desktop"), APP_NAME + ".lnk"),
            os.path.join(known_folder("programs"), APP_NAME + ".lnk"),
            os.path.join(known_folder("startup"), APP_NAME + ".lnk"))


def create_all_shortcuts(exe_path, with_desktop=True, with_startmenu=True, with_startup=True):
    ok = True
    desktop, startmenu, startup = shortcut_paths()
    if with_desktop:
        ok &= create_shortcut(desktop, exe_path, description=APP_NAME + " · 初中英语单词锁屏")
    if with_startmenu:
        ok &= create_shortcut(startmenu, exe_path, description=APP_NAME + " · 初中英语单词锁屏")
    if with_startup:
        ok &= create_shortcut(startup, exe_path, arguments="--silent",
                              description=APP_NAME + " · 开机静默启动")
    return ok


def remove_shortcuts():
    for path in shortcut_paths():
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    # 旧版（源码方式）留下的自启 bat
    legacy = os.path.join(known_folder("startup"), APP_NAME + ".bat")
    try:
        if os.path.exists(legacy):
            os.remove(legacy)
    except OSError:
        pass


def write_uninstall_registry(install_dir, exe_path):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        return False
    values = {"DisplayName": (APP_NAME + " - 初中英语单词锁屏", winreg.REG_SZ),
              "DisplayVersion": ("1.0.0", winreg.REG_SZ),
              "Publisher": (APP_NAME, winreg.REG_SZ),
              "DisplayIcon": (exe_path, winreg.REG_SZ),
              "InstallLocation": (install_dir, winreg.REG_SZ),
              "UninstallString": ('"%s" --uninstall' % exe_path, winreg.REG_SZ),
              "NoModify": (1, winreg.REG_DWORD),
              "NoRepair": (1, winreg.REG_DWORD)}
    for name, (value, kind) in values.items():
        winreg.SetValueEx(key, name, 0, kind, value)
    winreg.CloseKey(key)
    return True


def remove_uninstall_registry():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass


def stop_running_app(exe_name=EXE_NAME):
    """结束正在运行的实例（跳过自身）。"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", exe_name],
                       timeout=15, creationflags=CREATE_NO_WINDOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def schedule_dir_removal(directory, delay=3):
    """退出后删除整个安装目录（exe 自身无法在运行时删除自己）。"""
    bat = os.path.join(tempfile.gettempdir(), "sg_uninstall_%d.bat" % int(delay))
    content = ('@echo off\r\n'
               'timeout /t %d /nobreak >nul\r\n'
               'taskkill /F /IM %s >nul 2>&1\r\n'
               'timeout /t 1 /nobreak >nul\r\n'
               'rmdir /s /q "%s"\r\n'
               'del /f /q "%%~f0"\r\n') % (delay, EXE_NAME, directory)
    try:
        with open(bat, "w", encoding="gbk") as f:
            f.write(content)
        subprocess.Popen('cmd /c "%s"' % bat, creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False
