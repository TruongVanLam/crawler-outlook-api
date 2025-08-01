"""
Script để kiểm tra chi tiết về auth tokens
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

def check_tokens():
    """
    Kiểm tra chi tiết về auth tokens
    """
    print("🔍 KIỂM TRA AUTH TOKENS")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Lấy tất cả tokens
        tokens = db.query(AuthToken).all()
        
        print(f"📊 Tổng số tokens: {len(tokens)}")
        
        current_time = datetime.utcnow()
        print(f"⏰ Thời gian hiện tại: {current_time}")
        
        valid_count = 0
        expired_count = 0
        
        for token in tokens:
            print(f"\n🔑 Token ID: {token.id}")
            print(f"  - Account ID: {token.account_id}")
            print(f"  - Access Token: {token.access_token[:20]}..." if token.access_token else "  - Access Token: None")
            print(f"  - Refresh Token: {token.refresh_token[:20]}..." if token.refresh_token else "  - Refresh Token: None")
            print(f"  - Token Type: {token.token_type}")
            print(f"  - Expires At: {token.expires_at}")
            print(f"  - Is Active: {token.is_active}")
            
            # Kiểm tra token có hợp lệ không
            is_valid = (
                token.is_active and 
                token.expires_at and 
                token.expires_at > current_time
            )
            
            if is_valid:
                valid_count += 1
                print(f"  - ✅ Token hợp lệ")
                
                # Tính thời gian còn lại
                time_left = token.expires_at - current_time
                print(f"  - ⏰ Còn lại: {time_left}")
            else:
                expired_count += 1
                if not token.is_active:
                    print(f"  - ❌ Token không active")
                elif not token.expires_at:
                    print(f"  - ❌ Token không có thời gian hết hạn")
                else:
                    print(f"  - ❌ Token đã hết hạn")
                    time_expired = current_time - token.expires_at
                    print(f"  - ⏰ Đã hết hạn: {time_expired} trước")
        
        print(f"\n📈 Tổng kết:")
        print(f"  - Tokens hợp lệ: {valid_count}")
        print(f"  - Tokens hết hạn: {expired_count}")
        
        # Kiểm tra accounts có token không
        print(f"\n📋 Kiểm tra accounts:")
        accounts = db.query(Account).all()
        
        for account in accounts:
            account_tokens = db.query(AuthToken).filter(AuthToken.account_id == account.id).all()
            valid_account_tokens = [
                t for t in account_tokens 
                if t.is_active and t.expires_at and t.expires_at > current_time
            ]
            
            print(f"\n  📧 Account {account.id} ({account.email}):")
            print(f"    - Tổng tokens: {len(account_tokens)}")
            print(f"    - Tokens hợp lệ: {len(valid_account_tokens)}")
            
            if not valid_account_tokens:
                print(f"    - ⚠️ Cần refresh token cho account này")
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra tokens: {e}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành kiểm tra!")

if __name__ == "__main__":
    check_tokens() 