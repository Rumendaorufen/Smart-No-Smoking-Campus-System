from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from app.core.stream_loader import StreamManager
from app.models import init_db  # ✅ 1. 导入数据库初始化函数

# 1. 初始化全局扩展
# cors_allowed_origins="*" 允许前端跨域连接 WebSocket
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

# 2. 初始化全局视频流管理器
stream_manager = StreamManager()

def create_app():
    app = Flask(__name__)
    
    # ✅ 3. 加载配置文件 (连接数据库必须)
    try:
        from config import Config
        app.config.from_object(Config)
    except ImportError:
        print("⚠️ 警告：找不到 config.py，使用默认配置")
        # 默认回退配置，防止报错
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost/smart_campus_smoking'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ✅ 4. 初始化数据库 (这一步会创建表结构)
    init_db(app)

    # ✅ 5. 将 app 实例传给全局管理器
    # 这样录制线程才能通过 app.app_context() 访问数据库
    stream_manager.init_app(app)

    # 6. 配置跨域
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # 7. 绑定 SocketIO
    socketio.init_app(app)
    
    # 8. 注册蓝图 (Blueprints)
    from app.api.monitor import monitor_bp
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')
    
    # 如果有报警蓝图，也可以在这里取消注释
    # from app.api.alert import alert_bp
    # app.register_blueprint(alert_bp, url_prefix='/api/v1/alerts')

    return app