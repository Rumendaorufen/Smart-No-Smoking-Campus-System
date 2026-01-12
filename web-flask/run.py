import os

# ==========================================
# 🛑 全局环境配置 (必须在 import app 之前设置)
# ==========================================

# 1. 禁用 FFmpeg 内部多线程 (解决 "Assertion fctx->async_lock failed" 崩溃的关键!)
# 强制 FFmpeg 仅使用单线程解码，避免在 Flask 多线程环境下发生资源竞争
os.environ["OPENCV_FFMPEG_THREADS"] = "1"
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "threads;1"

# 2. 强制使用 FFmpeg 后端
# 禁用 Windows 默认的媒体基础库 (MSMF)，它对 RTSP 支持很差且容易卡死
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

# ==========================================
# 🚀 应用启动逻辑
# ==========================================

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("-------------------------------------------------------")
    print("🚀 智慧校园禁烟系统后端服务启动中...")
    print("📡 访问地址: http://0.0.0.0:5000")
    print("🔧 FFmpeg 单线程模式: 已启用 (防止崩溃)")
    print("-------------------------------------------------------")
    
    # 注意：使用 socketio.run 启动，而不是 app.run
    # allow_unsafe_werkzeug=True 允许在开发环境使用 Werkzeug 服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)