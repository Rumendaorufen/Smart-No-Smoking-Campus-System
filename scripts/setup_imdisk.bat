@echo off
REM scripts/setup_imdisk.bat
REM 创建 2GB 内存盘 R:\ 用于临时证据存储
REM ⚠️ 必须以管理员身份运行！

setlocal

:: 🚀 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ImDisk] 错误：请以管理员身份运行此脚本！
    echo [ImDisk] 右键点击 setup_imdisk.bat → 以管理员身份运行
    pause
    exit /b 1
)

:: 🚀 检查 imdisk.exe 是否可用
where imdisk >nul 2>&1
if %errorlevel% neq 0 (
    echo [ImDisk] 错误：未找到 imdisk.exe
    echo [ImDisk] 请确认已正确安装 ImDisk Toolkit
    pause
    exit /b 1
)

set RAMDISK_SIZE=2048
set RAMDISK_LETTER=R

echo [ImDisk] 正在创建 %RAMDISK_SIZE%MB 内存盘 %RAMDISK_LETTER%:\ ...

:: 如果已存在，先卸载
imdisk -d -m %RAMDISK_LETTER%:\ 2>nul

:: 创建新内存盘
imdisk -a -s %RAMDISK_SIZE%M -m %RAMDISK_LETTER%:\ -p "/fs:ntfs /q /y"

if %errorlevel% equ 0 (
    echo [ImDisk] 内存盘创建成功: %RAMDISK_LETTER%:\ (%RAMDISK_SIZE%MB)
    mkdir %RAMDISK_LETTER%:\evidence\snapshots 2>nul
    echo [ImDisk] 证据目录已创建: %RAMDISK_LETTER%:\evidence\snapshots
) else (
    echo [ImDisk] 创建失败
    pause
    exit /b 1
)

echo [ImDisk] 操作成功完成！
pause
