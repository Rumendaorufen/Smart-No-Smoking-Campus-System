from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # 强制 OpenCV 优先使用 FFmpeg，不使用 Windows 媒体基础库 (MSMF 有时会卡死 RTSP)
    import os
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    
    print("🚀 服务启动中...")
    print("🚀 服务启动: http://0.0.0.0:5000")
    # 注意：使用 socketio.run 启动，且 allow_unsafe_werkzeug=True 允许在开发环境使用
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)