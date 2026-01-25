#web-flask\app\models\devices.py
from app.models import db  # ✅ 关键：使用全局统一的 db 实例
from sqlalchemy.sql import func

class Devices(db.Model):  # ✅ 关键：继承 db.Model，而不是 Base
    __tablename__ = 'devices'

    # 使用 db.Column 替代 Column
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    rtsp_url = db.Column(db.String(500), nullable=False)
    area_config = db.Column(db.Text, nullable=True)
    status = db.Column(db.Integer, default=1)  # 1在线 0离线
    enabled = db.Column(db.Boolean, default=True)
    # 时间字段
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rtsp_url': self.rtsp_url,
            'status': self.status,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at)
        }