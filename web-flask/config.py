import os

from dotenv import load_dotenv


load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:change_me@localhost:3308/smart_campus_smoking?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
    # ✅ Java 后端地址配置 (在这里集中管理)
    # 1. 报警上报接口
    JAVA_API_URL = os.environ.get(
        'JAVA_API_URL', 'http://localhost:8080/api/internal/alarm/report'
    )
    # 2. 设备列表同步接口 (如果有的话)
    JAVA_DEVICE_LIST_URL = os.environ.get(
        'JAVA_DEVICE_LIST_URL', 'http://localhost:8080/api/monitor/devices'
    )
    
    # 视频流缓存配置 (保存最近 150 帧，约 5 秒)
    BUFFER_SIZE = 150  
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-local-env')

config = {
    'default': Config
}
