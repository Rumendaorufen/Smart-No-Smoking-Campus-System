# #web-flask\app\models\alarm.py
# from datetime import datetime
# from app.models import db

# class Alarms(db.Model):
#     __tablename__ = 'alarms'

#     id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
#     camera_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
#     type = db.Column(db.String(20), default='SMOKING', nullable=False)
#     confidence = db.Column(db.Float, nullable=False)
    
#     video_url = db.Column(db.String(255), nullable=False)
#     roi_url = db.Column(db.String(255), nullable=False)

#     # ✅ 匹配截图：使用 audit_status
#     audit_status = db.Column(db.Integer, default=0, index=True)

#     # ✅ 匹配截图：使用 auditor_id (外键)
#     auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
#     # ✅ 匹配截图：使用 audit_time 和 audit_remark
#     audit_time = db.Column(db.DateTime, nullable=True)
#     audit_remark = db.Column(db.String(255), nullable=True)

#     # ✅ 匹配截图：使用 created_at (不要用 create_time)
#     created_at = db.Column(db.DateTime, default=datetime.now, index=True)

#     # 关联关系
#     device = db.relationship('Devices', backref='alarms')
#     auditor = db.relationship('User', backref='audited_alarms')

#     def to_dict(self):
#         return {
#             'id': self.id,
#             'device_id': self.camera_id,
#             'device_name': self.device.name if self.device else f"未知设备({self.camera_id})",
#             'type': self.type,
#             'confidence': round(self.confidence, 2),
            
#             # ✅ 前端统一用 created_at
#             'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#             # ✅✅✅ 把审核人ID传给前端，用于权限判断
#             'auditor_id': self.auditor_id,
            
#             'video_url': self.video_url,
#             'roi_url': self.roi_url,
            
#             # ✅ 这里为了方便前端，依然返回 status 键，但值取 audit_status
#             'status': self.audit_status,
#             'status_text': self._get_status_text(),
            
#             'auditor_name': self.auditor.username if self.auditor else "-",
#             'audit_time': self.audit_time.strftime('%Y-%m-%d %H:%M:%S') if self.audit_time else "-",
#             'audit_remark': self.audit_remark or ""
#         }

#     def _get_status_text(self):
#         mapping = {0: '待审核', 1: '已确认', 2: '误报', 9: '已忽略'}
#         return mapping.get(self.audit_status, '未知')