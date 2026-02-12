# web-flask/app/__init__.py
from flask import Flask
from flask_cors import CORS
# 🚀 导入单例实例
from app.core.stream_loader import stream_manager

def create_app():
    app = Flask(__name__)
    
    # 1. 跨域配置 (保持现状，确保支持 credentials)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # 2. 🚀 关键修改：将单例绑定到 app 上
    # 这样在任何路由中通过 current_app.stream_manager 访问的都是同一个实例
    app.stream_manager = stream_manager
    
    # 初始化单例 (如果你的 init_app 内部有逻辑的话)
    stream_manager.init_app(app)

    # 3. 注册监控蓝图
    from app.api.monitor import monitor_bp
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')

    # 4. 注册系统控制蓝图
    from app.api.system import system_bp
    app.register_blueprint(system_bp, url_prefix='/api/v1/system')

    return app