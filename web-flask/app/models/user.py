# #web-flask\app\models\user.py
# from app.models import db
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime

# class User(db.Model):
#     __tablename__ = 'users'

#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     username = db.Column(db.String(50), unique=True, nullable=False)
#     # 数据库字段名是 password，这里映射为 password_hash，方便逻辑处理
#     password_hash = db.Column('password', db.String(255), nullable=False)
#     role = db.Column(db.String(20), default='user')
#     status = db.Column(db.Integer, default=1)
#     last_login_ip = db.Column(db.String(50))
#     last_login_time = db.Column(db.DateTime)
#     created_at = db.Column(db.DateTime, default=datetime.now)

#     @property
#     def password(self):
#         raise AttributeError('Password is not a readable attribute')

#     @password.setter
#     def password(self, password):
#         # 设置密码时自动加密
#         self.password_hash = generate_password_hash(password)

#     def verify_password(self, password):
#         # 验证密码时自动解密对比
#         return check_password_hash(self.password_hash, password)

#     def to_dict(self):
#         """返回给前端的用户信息（不包含密码）"""
#         return {
#             'id': self.id,
#             'username': self.username,
#             'role': self.role,
#             'status': self.status,  # ✅ 返回给前端，用于展示
#             'last_login_time': self.last_login_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_login_time else None,
#             'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#             'last_login_ip': self.last_login_ip
#         }