@echo off
rem 双击启动屏幕管控后台（无控制台窗口）
cd /d "%~dp0"
start "" pythonw "%~dp0main.py"
