param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$ExeName = "ScreenGuard.exe"
$Dest = Join-Path $env:LOCALAPPDATA "Programs\ScreenGuard"
$StartupFile = Join-Path ([Environment]::GetFolderPath('Startup')) "屏幕管控.bat"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ScreenGuard"

function Stop-App {
    Get-Process ScreenGuard -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 400
}

function New-Shortcut([string]$path, [string]$target, [string]$desc, [string]$arguments = "") {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $target
    $link.WorkingDirectory = (Split-Path -Parent $target)
    $link.IconLocation = "$target,0"
    $link.Description = $desc
    if ($arguments -ne "") { $link.Arguments = $arguments }
    $link.Save()
}

function Set-Autostart([string]$exePath) {
    # 优先用「启动」快捷方式（带 --silent 参数），失败再退化为 bat 脚本
    $lnk = Join-Path ([Environment]::GetFolderPath('Startup')) "屏幕管控.lnk"
    try {
        New-Shortcut $lnk $exePath "屏幕管控 · 开机静默启动" "--silent"
        return $true
    } catch {
        Write-Host "  启动快捷方式失败：$($_.Exception.Message)" -ForegroundColor Yellow
    }
    try {
        $bat = '@echo off' + "`r`n" + 'start "" "' + $exePath + '" --silent' + "`r`n"
        $bat | Out-File -FilePath $StartupFile -Encoding oem -Force
        return $true
    } catch {
        Write-Host "  开机自启写入失败：$($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

if ($Uninstall) {
    Write-Host "正在卸载【屏幕管控】..." -ForegroundColor Cyan
    Stop-App
    if (Test-Path $StartupFile) { Remove-Item $StartupFile -Force -ErrorAction SilentlyContinue }
    $startupLink = Join-Path ([Environment]::GetFolderPath('Startup')) "屏幕管控.lnk"
    if (Test-Path $startupLink) { Remove-Item $startupLink -Force -ErrorAction SilentlyContinue }
    $desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) "屏幕管控.lnk"
    if (Test-Path $desktopLink) { Remove-Item $desktopLink -Force -ErrorAction SilentlyContinue }
    $startLink = Join-Path ([Environment]::GetFolderPath('StartMenu')) "Programs\屏幕管控.lnk"
    if (Test-Path $startLink) { Remove-Item $startLink -Force -ErrorAction SilentlyContinue }
    if (Test-Path $UninstallKey) { Remove-Item $UninstallKey -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host "已卸载完成（学习记录已一并清除）。" -ForegroundColor Green
    Start-Sleep -Seconds 1
    exit 0
}

Write-Host "正在安装【屏幕管控 · 初中英语单词锁屏】..." -ForegroundColor Cyan

$source = Join-Path $PSScriptRoot "ScreenGuard"
if (-not (Test-Path (Join-Path $source $ExeName))) {
    Write-Host "安装失败：未找到 $ExeName，请保证安装包目录完整。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Stop-App
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# 复制程序文件（合并覆盖，不删除已有的 data 目录，保留学习记录）
Write-Host "  正在复制程序文件到 $Dest ..."
Copy-Item -Path (Join-Path $source "*") -Destination $Dest -Recurse -Force

# 快捷方式
New-Shortcut (Join-Path ([Environment]::GetFolderPath('Desktop')) "屏幕管控.lnk") `
    (Join-Path $Dest $ExeName) "屏幕管控 · 初中英语单词锁屏"
New-Item -ItemType Directory -Force -Path (Join-Path ([Environment]::GetFolderPath('StartMenu')) "Programs") | Out-Null
New-Shortcut (Join-Path ([Environment]::GetFolderPath('StartMenu')) "Programs\屏幕管控.lnk") `
    (Join-Path $Dest $ExeName) "屏幕管控 · 初中英语单词锁屏"

# 开机自启（静默启动，只显示托盘图标）
if (Set-Autostart (Join-Path $Dest $ExeName)) {
    Write-Host "  开机自启：已添加（启动时静默运行）"
} else {
    Write-Host "  开机自启：添加失败，请在后台「密码与安全」里手动开启" -ForegroundColor Yellow
}

# 注册卸载信息（显示在 Windows「应用和功能」列表）
try {
    New-Item -Path $UninstallKey -Force | Out-Null
    Set-ItemProperty -Path $UninstallKey -Name DisplayName -Value "屏幕管控 - 初中英语单词锁屏"
    Set-ItemProperty -Path $UninstallKey -Name DisplayVersion -Value "1.0.0"
    Set-ItemProperty -Path $UninstallKey -Name Publisher -Value "屏幕管控"
    Set-ItemProperty -Path $UninstallKey -Name DisplayIcon -Value (Join-Path $Dest $ExeName)
    Set-ItemProperty -Path $UninstallKey -Name InstallLocation -Value $Dest
    Set-ItemProperty -Path $UninstallKey -Name UninstallString -Value ('"' + (Join-Path $Dest $ExeName) + '" --uninstall')
    Set-ItemProperty -Path $UninstallKey -Name NoModify -Value 1 -Type DWord
    Set-ItemProperty -Path $UninstallKey -Name NoRepair -Value 1 -Type DWord
} catch {
    Write-Host "  注册卸载信息失败：$($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "安装完成：" -ForegroundColor Green
Write-Host "  程序目录：$Dest"
Write-Host "  桌面 / 开始菜单已创建快捷方式，已加入开机启动。"
Write-Host "  首次运行请在「密码与安全」里设置家长密码。" -ForegroundColor Yellow

Start-Process (Join-Path $Dest $ExeName)
Start-Sleep -Seconds 1
