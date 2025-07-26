"""
Migration script để thêm bảng users và cập nhật bảng accounts
Chạy script này để cập nhật database schema
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def run_migration():
    """Chạy migration để thêm bảng users và cập nhật accounts"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Tạo bảng users
        print("🔄 Tạo bảng users...")
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Thêm index cho email
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """))
        
        # Thêm trường user_id vào bảng accounts nếu chưa có
        print("🔄 Cập nhật bảng accounts...")
        try:
            connection.execute(text("""
                ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_id INTEGER;
            """))
        except Exception as e:
            print(f"⚠️ Trường user_id có thể đã tồn tại: {e}")
        
        # Thêm foreign key constraint
        try:
            connection.execute(text("""
                ALTER TABLE accounts 
                ADD CONSTRAINT fk_accounts_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id);
            """))
        except Exception as e:
            print(f"⚠️ Foreign key constraint có thể đã tồn tại: {e}")
        
        # Commit changes
        connection.commit()
        
        print("✅ Migration hoàn thành!")
        print("📋 Các thay đổi:")
        print("   - Tạo bảng users với các trường: id, email, password_hash, role, created_at, updated_at")
        print("   - Thêm trường user_id vào bảng accounts")
        print("   - Thêm foreign key constraint giữa accounts và users")

if __name__ == "__main__":
    run_migration() 