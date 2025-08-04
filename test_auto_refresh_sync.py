"""
Script để test auto refresh token trước khi sync
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
from app.services import EmailSyncService
from app.meta_receipt_service import MetaReceiptService
from app.auth import refresh_access_token

def test_auto_refresh_sync():
    """
    Test auto refresh token trước khi sync
    """
    print("🔄 TEST AUTO REFRESH TOKEN TRƯỚC KHI SYNC")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        print(f"⏰ Thời gian hiện tại: {current_time}")
        
        # Lấy tất cả accounts có token (kể cả hết hạn)
        accounts = db.query(Account).join(AuthToken).filter(
            and_(
                Account.is_active == True,
                AuthToken.is_active == True
            )
        ).all()
        
        print(f"📊 Tìm thấy {len(accounts)} accounts có token")
        
        if not accounts:
            print("❌ Không có account nào có token")
            return
        
        total_emails_synced = 0
        total_receipts_processed = 0
        refreshed_tokens = 0
        
        for account in accounts:
            try:
                print(f"\n📧 Đang xử lý account {account.id} ({account.email})...")
                
                # Kiểm tra token
                auth_token = db.query(AuthToken).filter(
                    and_(
                        AuthToken.account_id == account.id,
                        AuthToken.is_active == True
                    )
                ).first()
                
                if not auth_token:
                    print(f"❌ Account {account.id} không có token")
                    continue
                
                print(f"⏰ Token expires at: {auth_token.expires_at}")
                
                # Kiểm tra và refresh token nếu cần
                if auth_token.expires_at <= current_time:
                    print(f"🔄 Token đã hết hạn, đang refresh...")
                    try:
                        refresh_access_token(db, account.id)
                        refreshed_tokens += 1
                        print(f"✅ Token đã được refresh thành công")
                        
                        # Lấy token đã được cập nhật
                        updated_token = db.query(AuthToken).filter(
                            AuthToken.account_id == account.id
                        ).first()
                        print(f"⏰ Token mới expires at: {updated_token.expires_at}")
                    except Exception as e:
                        print(f"❌ Lỗi khi refresh token: {str(e)}")
                        continue
                else:
                    print(f"✅ Token còn hợp lệ")
                
                # Thực hiện daily sync
                sync_service = EmailSyncService(db, account.id)
                result = sync_service.sync_daily_emails()
                
                emails_synced = result['total_synced']
                total_emails_synced += emails_synced
                
                print(f"✅ Daily sync hoàn thành: {emails_synced} emails mới")
                
                if emails_synced > 0:
                    # Xử lý meta receipts cho emails mới
                    meta_service = MetaReceiptService(db)
                    meta_result = meta_service.process_account_emails(account.id)
                    
                    receipts_processed = meta_result['processed_count']
                    total_receipts_processed += receipts_processed
                    
                    print(f"📄 Meta receipts đã xử lý: {receipts_processed} receipts")
                else:
                    print("ℹ️ Không có email mới")
                    
            except Exception as e:
                print(f"❌ Lỗi khi xử lý account {account.id}: {str(e)}")
                continue
        
        print(f"\n📈 Tổng kết:")
        print(f"  - Accounts đã xử lý: {len(accounts)}")
        print(f"  - Tokens đã refresh: {refreshed_tokens}")
        print(f"  - Tổng emails đã sync: {total_emails_synced}")
        print(f"  - Tổng receipts đã xử lý: {total_receipts_processed}")
        
    except Exception as e:
        print(f"❌ Lỗi chung: {str(e)}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành test auto refresh sync!")

if __name__ == "__main__":
    test_auto_refresh_sync() 