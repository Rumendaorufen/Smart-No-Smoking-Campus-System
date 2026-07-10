import os

from dotenv import load_dotenv


load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:change_me@localhost:3308/smart_campus_smoking?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
    JAVA_BASE_URL = os.environ.get('JAVA_BASE_URL', 'http://localhost:8080').rstrip('/')
    JAVA_API_URL = os.environ.get(
        'JAVA_API_URL', f'{JAVA_BASE_URL}/api/internal/alarm/report'
    )
    JAVA_DEVICE_LIST_URL = os.environ.get(
        'JAVA_DEVICE_LIST_URL', f'{JAVA_BASE_URL}/api/internal/devices'
    )
    JAVA_STATUS_SYNC_URL = os.environ.get(
        'JAVA_STATUS_SYNC_URL', f'{JAVA_BASE_URL}/api/monitor/devices/sync-status'
    )
    JAVA_BATCH_SYNC_URL = os.environ.get(
        'JAVA_BATCH_SYNC_URL', f'{JAVA_BASE_URL}/api/monitor/devices/batch-sync'
    )
    INTERNAL_API_TOKEN = os.environ.get('INTERNAL_API_TOKEN', '').strip()
    
    # 视频流缓存配置 (保存最近 150 帧，约 5 秒)
    BUFFER_SIZE = 150  
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-local-env')

config = {
    'default': Config
}
