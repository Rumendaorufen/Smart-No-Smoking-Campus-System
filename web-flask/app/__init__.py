from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
# ✅ 1. 引入 JWTManager
from flask_jwt_extended import JWTManager
from app.core.stream_loader import StreamManager
from app.models import init_db

# 1. 初始化全局扩展
# cors_allowed_origins="*" 允许前端跨域连接 WebSocket
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
# # 显式指定 'eventlet'，或者留空让它自动检测，但不要强制设为 'threading' (性能差)
# socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

# ✅ 2. 实例化 JWT
jwt = JWTManager()

# 3. 初始化全局视频流管理器
stream_manager = StreamManager()

def create_app():
    app = Flask(__name__)
    
    # 4. 加载配置文件 (连接数据库必须)
    try:
        from config import Config
        app.config.from_object(Config)
    except ImportError:
        print("⚠️ 警告：找不到 config.py，使用默认配置")
        # 默认回退配置，防止报错
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost/smart_campus_smoking'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ✅ 5. JWT 配置 (必须设置密钥)
    # 生产环境中，这个密钥应该从环境变量读取，且非常复杂
    app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this-in-production"  
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600 * 24  # Token 有效期设置为 1 天

    # 6. 初始化数据库 (这一步会创建表结构)
    init_db(app)

    # 7. 将 app 实例传给全局管理器
    # 这样录制线程才能通过 app.app_context() 访问数据库
    stream_manager.init_app(app)

    # 8. 配置跨域
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # 9. 绑定扩展
    socketio.init_app(app)
    jwt.init_app(app)  # ✅ 绑定 JWT
    
    # 10. 注册蓝图 (Blueprints)
    from app.api.monitor import monitor_bp
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')
    
    # ✅ 注册认证蓝图 (处理登录接口)
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')

    # ✅ 新增：注册用户管理蓝图
    # 注意 URL 前缀是 /api/v1/users
    from app.api.user import user_bp
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')

    from app.api.alert import alert_bp  # 👈 新增导入
    app.register_blueprint(alert_bp, url_prefix='/api/v1/alerts') # 👈 注册路径

    return app