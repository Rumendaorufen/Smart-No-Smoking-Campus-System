# app/models.py
from app import db  # 确保你的 app/__init__.py 里初始化了 db 对象

# 1. 设备表 (Devices)
class Devices(db.Model):
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, comment='设备名称')
    rtsp_url = db.Column(db.String(500), nullable=False, comment='RTSP流地址')
    area_config = db.Column(db.Text, nullable=True, comment='ROI区域配置(JSON)')
    status = db.Column(db.Integer, default=1, comment='1在线 0离线')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rtsp_url': self.rtsp_url,
            'status': self.status
        }

# 2. 报警表 (Alarms) - 后面也会用到
class Alarms(db.Model):
    __tablename__ = 'alarms'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False, comment='事件类型: SMOKING/FIRE')
    confidence = db.Column(db.Float, default=0.0)
    video_path = db.Column(db.String(255), comment='证据视频路径')
    image_path = db.Column(db.String(255), comment='抓拍图片路径')
    status = db.Column(db.Integer, default=0, comment='0待审核 1已确认 2忽略')
    create_time = db.Column(db.DateTime, default=db.func.now())