"""
Script để refresh tất cả tokens đã hết hạn
"""
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Thêm thư mục hiện tại vào path để import các module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Account, AuthToken
from app.auth import refresh_access_token

def refresh_expired_tokens():
    """
    Refresh tất cả tokens đã hết hạn
    """
    print("🔄 REFRESH EXPIRED TOKENS")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        
        # Lấy tất cả tokens đã hết hạn
        expired_tokens = db.query(AuthToken).filter(
            and_(
                AuthToken.is_active == True,
                AuthToken.expires_at < current_time
            )
        ).all()
        
        print(f"📊 Tìm thấy {len(expired_tokens)} tokens đã hết hạn")
        
        if not expired_tokens:
            print("✅ Không có token nào cần refresh")
            return
        
        success_count = 0
        error_count = 0
        
        for token in expired_tokens:
            try:
                print(f"\n🔄 Đang refresh token cho account {token.account_id}...")
                
                # Lấy thông tin account
                account = db.query(Account).filter(Account.id == token.account_id).first()
                if not account:
                    print(f"❌ Không tìm thấy account {token.account_id}")
                    error_count += 1
                    continue
                
                print(f"📧 Email: {account.email}")
                print(f"⏰ Token hết hạn: {token.expires_at}")
                
                # Refresh token
                new_access_token = refresh_access_token(db, token.account_id)
                
                if new_access_token:
                    # Lấy token đã được cập nhật
                    updated_token = db.query(AuthToken).filter(AuthToken.account_id == token.account_id).first()
                    
                    print(f"✅ Token đã được refresh thành công")
                    print(f"⏰ Hết hạn mới: {updated_token.expires_at}")
                    success_count += 1
                else:
                    print(f"❌ Không thể refresh token")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Lỗi khi refresh token cho account {token.account_id}: {str(e)}")
                error_count += 1
                continue
        
        print(f"\n📈 Tổng kết:")
        print(f"  - Tokens refresh thành công: {success_count}")
        print(f"  - Tokens lỗi: {error_count}")
        
        # Kiểm tra lại sau khi refresh
        valid_tokens = db.query(AuthToken).filter(
            and_(
                AuthToken.is_active == True,
                AuthToken.expires_at > current_time
            )
        ).count()
        
        print(f"  - Tokens hợp lệ hiện tại: {valid_tokens}")
        
    except Exception as e:
        print(f"❌ Lỗi chung: {str(e)}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành refresh tokens!")

if __name__ == "__main__":
    refresh_expired_tokens() 