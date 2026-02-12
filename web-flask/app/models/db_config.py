# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from config import Config

# # 创建引擎
# engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, 
#                        pool_size=10, 
#                        pool_recycle=3600,
#                        echo=False)

# # 创建会话工厂
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # 创建模型基类
# Base = declarative_base()

# # 数据库依赖注入函数
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()