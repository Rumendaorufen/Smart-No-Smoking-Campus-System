from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("🚀 服务启动中: http://0.0.0.0:5000")
    # 注意：使用 socketio.run 启动，且 allow_unsafe_werkzeug=True 允许在开发环境使用
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)