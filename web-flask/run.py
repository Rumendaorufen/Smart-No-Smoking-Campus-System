# web-flask/run.py

import os
import threading
import time
from app import create_app

# 🚀 删掉下面这一行，它导致了 ImportError
# from app.api.monitor import init_streams_from_java 

app = create_app()

# 如果你还是想保留启动同步，可以写一个简单的逻辑，
# 或者干脆注释掉 start_sync_thread 相关的调用。
def start_sync_thread():
    """现在的同步逻辑已经在 monitor.py 的接口里自动实现了"""
    pass

if __name__ == '__main__':
    print("🚀 智慧校园 AI 引擎启动中...")
    # 保持 use_reloader=False 
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)