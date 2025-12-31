import os

class Config:
    # 🔴 请务必修改为你的 MySQL 密码
    # 格式: mysql+pymysql://用户名:密码@地址:端口/数据库名
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost:3308/smart_campus_smoking?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 视频流缓存配置 (保存最近 150 帧，约 5 秒)
    BUFFER_SIZE = 150  
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'

config = {
    'default': Config
}