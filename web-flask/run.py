"""Flask 视觉服务启动入口。

当前运行架构只使用 create_app() 中初始化的全局 StreamManager。
摄像头由 Java 设备列表动态同步，避免再启动固定 camera ID 分片的
WorkerManager，造成重复拉流、重复模型实例和重复报警。
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
