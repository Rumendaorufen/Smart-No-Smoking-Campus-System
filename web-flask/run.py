"""
🚀 Windows 多进程安全启动入口。

⚠️ WorkerManager 的初始化必须在 if __name__ == '__main__' 块内，
绝不能放在 create_app() 中。Windows 的 spawn 机制会重新运行
模块顶级代码，如果在 create_app 中启动 Workers，子进程会递归
衍生孙子进程，导致进程爆炸。
"""
from app import create_app
from app.core.worker_manager import WorkerManager

app = create_app()

if __name__ == '__main__':
    print("[Master] 正在初始化多进程视觉分片引擎...")
    worker_mgr = WorkerManager(camera_count=200, workers_per_gpu=4)
    worker_mgr.start()

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)