from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from app.core.stream_loader import StreamManager

# 1. 初始化扩展 (全局对象)
# cors_allowed_origins="*" 允许前端跨域连接 WebSocket
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

# 2. 初始化全局视频流管理器
# 这样 monitor.py 就可以通过 "from app import stream_manager" 访问同一个实例
stream_manager = StreamManager()

def create_app():
    app = Flask(__name__)
    
    # 3. 配置跨域
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # 4. 绑定扩展
    socketio.init_app(app)
    
    # 5. 注册蓝图 (Blueprints)
    from app.api.monitor import monitor_bp
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')
    
    # 如果你有其他蓝图（比如 auth, alert），也在这里注册
    # from app.api.alert import alert_bp
    # app.register_blueprint(alert_bp, url_prefix='/api/v1/monitor')

    return app