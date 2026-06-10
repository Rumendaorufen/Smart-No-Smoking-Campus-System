@echo off
REM web-flask/scripts/start_mediamtx.bat
REM MediaMTX 启动脚本 — 在后台静默运行
REM 使用 %~dp0 获取脚本所在目录，确保路径绝对可靠

setlocal

:: 脚本所在目录的上级目录（即 web-flask/）
set "BASE_DIR=%~dp0.."
cd /d "%BASE_DIR%"
mkdir logs 2>nul

:: mediamtx.exe 和 mediamtx.yml 都放在 web-flask/ 根目录
set "MTX_EXE=%BASE_DIR%\mediamtx.exe"
set "MTX_YML=%BASE_DIR%\mediamtx.yml"

if not exist "%MTX_EXE%" (
    echo [MediaMTX] 错误: 未找到 %MTX_EXE%
    echo [MediaMTX] 请将 Windows 版 mediamtx.exe 放置于 web-flask/ 根目录下
    exit /b 1
)

echo [MediaMTX] 正在启动 RTSP 代理网关...
start /B /MIN "" "%MTX_EXE%" "%MTX_YML%"
if %errorlevel% equ 0 (
    echo [MediaMTX] 启动成功，监听端口 8554
) else (
    echo [MediaMTX] 启动失败
    exit /b 1
)
