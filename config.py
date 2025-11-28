import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Cililin-lin-bei-key')
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/rent_house'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    # 添加数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'pool_timeout': 30
    }
