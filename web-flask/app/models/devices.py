from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.models.db_config import Base

class Devices(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    area_config = Column(Text, nullable=True)
    status = Column(Integer, default=1) # 1在线 0离线
    
    # 时间字段
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rtsp_url': self.rtsp_url,
            'status': self.status,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at)
        }