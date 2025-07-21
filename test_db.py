#!/usr/bin/env python3
"""
Script test để kiểm tra việc tạo bảng database
"""

import os
from dotenv import load_dotenv
from database import engine, create_tables, drop_tables
from models import Account, AuthToken, Email, EmailAttachment

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test kết nối database"""
    try:
        # Test kết nối
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            print("✅ Kết nối database thành công!")
            return True
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False

def test_create_tables():
    """Test tạo bảng"""
    try:
        print("🔄 Đang tạo bảng...")
        create_tables()
        print("✅ Tạo bảng thành công!")
        
        # Kiểm tra bảng đã được tạo
        with engine.connect() as connection:
            # Kiểm tra bảng accounts
            result = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result]
            print(f"📋 Các bảng đã tạo: {tables}")
            
            # Kiểm tra cấu trúc bảng accounts
            result = connection.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'accounts' 
                ORDER BY ordinal_position
            """)
            print("\n📊 Cấu trúc bảng accounts:")
            for row in result:
                print(f"  - {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
                
        return True
    except Exception as e:
        print(f"❌ Lỗi tạo bảng: {e}")
        return False

def test_drop_tables():
    """Test xóa bảng"""
    try:
        print("🔄 Đang xóa bảng...")
        drop_tables()
        print("✅ Xóa bảng thành công!")
        return True
    except Exception as e:
        print(f"❌ Lỗi xóa bảng: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Bắt đầu test database...")
    print(f"📡 Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print("-" * 50)
    
    # Test kết nối
    if not test_database_connection():
        return
    
    print("-" * 50)
    
    # Test tạo bảng
    if test_create_tables():
        print("-" * 50)
        
        # Hỏi có muốn xóa bảng không
        response = input("❓ Bạn có muốn xóa bảng để test lại không? (y/N): ")
        if response.lower() == 'y':
            test_drop_tables()
    
    print("-" * 50)
    print("✅ Test hoàn thành!")

if __name__ == "__main__":
    main() 