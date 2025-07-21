#!/usr/bin/env python3
"""
Script kiểm tra kết nối database và tạo bảng
"""

import os
import sys

def check_env_file():
    """Kiểm tra file .env"""
    print("🔍 Kiểm tra file .env...")
    
    if os.path.exists('.env'):
        print("✅ File .env tồn tại")
        try:
            with open('.env', 'r') as f:
                content = f.read()
                print(f"📄 Nội dung file .env:")
                print(content)
        except Exception as e:
            print(f"❌ Lỗi đọc file .env: {e}")
    else:
        print("❌ File .env không tồn tại")
        return False
    
    return True

def check_database_connection():
    """Kiểm tra kết nối database"""
    print("\n🔍 Kiểm tra kết nối database...")
    
    try:
        from database import engine, DATABASE_URL
        
        print(f"📡 DATABASE_URL: {DATABASE_URL}")
        
        # Test kết nối
        with engine.connect() as connection:
            from sqlalchemy import text
            result = connection.execute(text("SELECT 1"))
            print("✅ Kết nối database thành công!")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False

def check_create_tables():
    """Kiểm tra tạo bảng"""
    print("\n🔍 Kiểm tra tạo bảng...")
    
    try:
        from database import engine, create_tables
        
        # Import models để đảm bảo chúng được đăng ký với Base
        import models
        
        print("🔄 Đang tạo bảng...")
        create_tables()
        print("✅ Tạo bảng thành công!")
        
        # Kiểm tra bảng đã được tạo
        with engine.connect() as connection:
            from sqlalchemy import text
            result = connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            print(f"📋 Các bảng đã tạo: {tables}")
            
            if tables:
                # Kiểm tra cấu trúc bảng accounts
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'accounts' 
                    ORDER BY ordinal_position
                """))
                print("\n📊 Cấu trúc bảng accounts:")
                for row in result:
                    print(f"  - {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi tạo bảng: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🚀 Bắt đầu kiểm tra database...")
    print("=" * 50)
    
    # Kiểm tra file .env
    if not check_env_file():
        print("\n❌ Không thể tiếp tục vì file .env không tồn tại")
        return
    
    # Kiểm tra kết nối database
    if not check_database_connection():
        print("\n❌ Không thể tiếp tục vì không kết nối được database")
        return
    
    # Kiểm tra tạo bảng
    if not check_create_tables():
        print("\n❌ Không thể tạo bảng")
        return
    
    print("\n" + "=" * 50)
    print("✅ Tất cả kiểm tra đều thành công!")
    print("🎉 Database đã sẵn sàng sử dụng!")

if __name__ == "__main__":
    main() 