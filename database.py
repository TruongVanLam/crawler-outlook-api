from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
try:
    with open('.env') as f:
        env_vars = {}
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
        
        # Tạo DATABASE_URL từ các biến môi trường
        if 'POSTGRES_HOST' in env_vars:
            host = env_vars['POSTGRES_HOST']
            port = env_vars.get('POSTGRES_PORT', '5432')
            db = env_vars.get('POSTGRES_DB', 'outlook_crawler')
            user = env_vars.get('POSTGRES_USER', 'postgres')
            password = env_vars.get('POSTGRES_PASSWORD', '123456')
            
            DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        else:
            # Fallback nếu không tìm thấy biến môi trường
            DATABASE_URL = "postgresql://postgres:123456@160.25.88.158:5432/outlook_crawler"
            
except FileNotFoundError:
    DATABASE_URL = "postgresql://postgres:123456@160.25.88.158:5432/outlook_crawler"
except Exception as e:
    print(f"Lỗi đọc file .env: {e}")
    DATABASE_URL = "postgresql://postgres:123456@160.25.88.158:5432/outlook_crawler"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Kiểm tra kết nối trước khi sử dụng
    pool_recycle=300,    # Recycle connections after 5 minutes
    echo=False           # Set to True để log SQL queries
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Tạo tất cả bảng trong database"""
    # Import models để đảm bảo chúng được đăng ký với Base
    import models
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Xóa tất cả bảng trong database"""
    # Import models để đảm bảo chúng được đăng ký với Base
    import models
    Base.metadata.drop_all(bind=engine) 