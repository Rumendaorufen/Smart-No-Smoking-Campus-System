# from app import create_app
# from app.models import db
# from app.models.user import User
# from datetime import datetime

# app = create_app()

# def init_admin():
#     with app.app_context():
#         # 1. 检查是否已存在 admin
#         if User.query.filter_by(username='admin').first():
#             print("⚠️ 管理员账号 'admin' 已存在，跳过创建。")
#             return

#         print("🚀 正在创建初始管理员账号...")
        
#         # 2. 实例化用户对象并填充所有字段
#         admin = User()
        
#         # --- 必填字段 ---
#         admin.username = 'admin'
#         admin.password = '123456'  # 自动触发 @password.setter 进行加密
#         admin.role = 'admin'
        
#         # --- 可选字段 (设置初始状态) ---
#         # 刚创建时，最后登录时间和IP通常为空，或者设置为当前时间/本地IP作为初始记录
#         admin.last_login_time = datetime.now()  # 设置为创建时间
#         admin.last_login_ip = '127.0.0.1'       # 初始 IP 设为本地
        
#         # --- 自动字段 (虽然数据库有默认值，但Python层面也可以显式赋值) ---
#         admin.created_at = datetime.now()

#         # 3. 提交到数据库
#         try:
#             db.session.add(admin)
#             db.session.commit()
#             print("---------------------------------------------")
#             print("✅ 管理员创建成功！")
#             print(f"👤 账号: {admin.username}")
#             print(f"🔑 密码: 123456")
#             print(f"🛡️ 角色: {admin.role}")
#             print(f"📅 时间: {admin.created_at}")
#             print("---------------------------------------------")
#         except Exception as e:
#             db.session.rollback()
#             print(f"❌ 创建失败: {str(e)}")

# if __name__ == '__main__':
#     init_admin()