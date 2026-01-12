# web-flask/app/models/alarm.py
from app.models import db
from datetime import datetime

class Alarms(db.Model):
    __tablename__ = 'alarms'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    type = db.Column(db.Enum('SMOKING', 'FIRE'), nullable=False, default='SMOKING')
    confidence = db.Column(db.Float, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)
    video_url = db.Column(db.String(255), nullable=False) # 视频路径
    roi_url = db.Column(db.String(255), nullable=False)   # 图片路径
    audit_status = db.Column(db.Integer, default=0)       # 0待审核
    auditor = db.Column(db.String(50), nullable=True)
    audit_time = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'type': self.type,
            'confidence': self.confidence,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'video_url': self.video_url,
            'roi_url': self.roi_url,
            'audit_status': self.audit_status
        }