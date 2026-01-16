from flask_sqlalchemy import SQLAlchemy

# 1. 创建全局 db 对象
db = SQLAlchemy()

# 2. 初始化函数
def init_db(app):
    db.init_app(app)
    
    # 显式导入模型，防止 create_all 找不到表
    from app.models.devices import Devices
    from app.models.user import User    # 👈 新增
    from app.models.alarm import Alarms
    
    with app.app_context():
        db.create_all()
        print("✅ 数据库初始化完成")

# 3. 导出模型，方便外部引用
# (使用了 try-except 是为了防止循环导入时的报错，保持健壮性)
try:
    from app.models.devices import Devices
    from app.models.user import User    # 👈 新增
    from app.models.alarm import Alarms
except ImportError:
    pass