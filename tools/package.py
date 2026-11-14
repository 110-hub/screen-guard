# -*- coding: utf-8 -*-
"""一键打包：PyInstaller 生成 exe + 组装中文安装包 + 打 zip。"""
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "ScreenGuard")
RELEASE = os.path.join(ROOT, "发布")
SETUP_DIR = os.path.join(RELEASE, "屏幕管控安装包")
ZIP_PATH = os.path.join(RELEASE, "屏幕管控安装包.zip")
INSTALLER = os.path.join(ROOT, "installer")


def run(cmd):
    print(">>", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit("构建失败，退出码 %d" % result.returncode)


def main():
    print("[1/4] 生成图标")
    run([sys.executable, os.path.join("tools", "make_icon.py")])

    print("[2/4] 打包 exe")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
         "--name", "ScreenGuard",
         "--icon", os.path.join("assets", "icon.ico"),
         "--add-data", "data/words;data/words",
         "--hidden-import", "pystray._win32",
         "--hidden-import", "PIL._tkinter_finder",
         "main.py"])

    print("[3/4] 组装安装包")
    if os.path.isdir(RELEASE):
        shutil.rmtree(RELEASE, ignore_errors=True)
    test_data = os.path.join(DIST, "data")
    if os.path.isdir(test_data):
        shutil.rmtree(test_data, ignore_errors=True)     # 清掉测试残留，安装后首次运行会重新生词库
    os.makedirs(SETUP_DIR, exist_ok=True)
    shutil.copytree(DIST, os.path.join(SETUP_DIR, "ScreenGuard"))
    for name in ("install.ps1", "安装.bat", "卸载.bat", "安装说明.txt"):
        shutil.copy2(os.path.join(INSTALLER, name), os.path.join(SETUP_DIR, name))
    shutil.copy2(os.path.join(ROOT, "README.md"), os.path.join(SETUP_DIR, "使用说明.md"))

    print("[4/5] 生成 zip")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(SETUP_DIR):
            for name in files:
                full = os.path.join(base, name)
                rel = os.path.relpath(full, SETUP_DIR)
                zf.write(full, os.path.join("屏幕管控安装包", rel))

    print("[5/5] 生成单文件安装程序（约需 1 分钟）")
    payload_zip = os.path.join(ROOT, "build", "payload.zip")
    os.makedirs(os.path.dirname(payload_zip), exist_ok=True)
    if os.path.exists(payload_zip):
        os.remove(payload_zip)
    with zipfile.ZipFile(payload_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(DIST):
            for name in files:
                full = os.path.join(base, name)
                rel = os.path.relpath(full, DIST).replace(os.sep, "/")
                zf.write(full, rel)

    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
         "--windowed",
         "--name", "屏幕管控安装程序",
         "--icon", os.path.join("assets", "icon.ico"),
         "--add-data", payload_zip + ";.",
         "--add-data", "assets/icon.ico;.",
         "--paths", ROOT,
         "--distpath", RELEASE,
         "--workpath", os.path.join("build", "setup"),
         os.path.join("installer", "setup_app.py")])

    setup_exe = os.path.join(RELEASE, "屏幕管控安装程序.exe")
    size = os.path.getsize(ZIP_PATH) / 1024.0 / 1024.0
    exe_size = os.path.getsize(os.path.join(SETUP_DIR, "ScreenGuard", "ScreenGuard.exe"))
    print("\n完成！")
    print("  单文件安装程序：%s（%.1f MB）双击即可安装"
          % (setup_exe, os.path.getsize(setup_exe) / 1024.0 / 1024.0))
    print("  绿色包目录：%s" % SETUP_DIR)
    print("  绿色包压缩：%s（%.1f MB）" % (ZIP_PATH, size))
    print("  主程序：ScreenGuard.exe（%.1f MB）" % (exe_size / 1024.0 / 1024.0))


if __name__ == "__main__":
    main()
