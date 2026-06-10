@echo off
REM scripts/setup_imdisk.bat
REM 创建 2GB 内存盘 R:\ 用于临时证据存储

setlocal
set RAMDISK_SIZE=2048  rem MB
set RAMDISK_LETTER=R

echo [ImDisk] 正在创建 %RAMDISK_SIZE%MB 内存盘 %RAMDISK_LETTER%:\ ...

:: 如果已存在，先卸载
imdisk -d -m %RAMDISK_LETTER%:\ 2>nul

:: 创建新内存盘
imdisk -a -s %RAMDISK_SIZE%M -m %RAMDISK_LETTER%:\ -p "/fs:ntfs /q /y"

if %errorlevel% equ 0 (
    echo [ImDisk] 内存盘创建成功: %RAMDISK_LETTER%:\ (%RAMDISK_SIZE%MB)
    mkdir %RAMDISK_LETTER%:\evidence\snapshots 2>nul
) else (
    echo [ImDisk] 创建失败！请确保已安装 ImDisk Toolkit
    exit /b 1
)
