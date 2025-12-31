from flask import Flask
from flask_cors import CORS
from app.models.db_config import Base, engine

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # 允许跨域
    CORS(app)
    
    # 初始化数据库表 (如果表不存在会自动创建)
    Base.metadata.create_all(bind=engine)
    
    # 注册蓝图
    from app.api.monitor import monitor_bp
    from app.api.auth import auth_bp
    from app.api.alert import alert_bp
    
    # 添加 /api/v1 前缀，与前端保持一致
    app.register_blueprint(monitor_bp, url_prefix='/api/v1/monitor')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(alert_bp, url_prefix='/api/v1/alert')
    
    return app