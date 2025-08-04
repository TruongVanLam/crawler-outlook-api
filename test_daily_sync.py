"""
Script để test daily sync thủ công
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

def test_daily_sync():
    """
    Test daily sync thủ công
    """
    print("🔄 TEST DAILY SYNC THỦ CÔNG")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        print(f"⏰ Thời gian hiện tại: {current_time}")
        
        # Lấy tất cả accounts có token hợp lệ
        active_accounts = db.query(Account).join(AuthToken).filter(
            and_(
                Account.is_active == True,
                AuthToken.is_active == True,
                AuthToken.expires_at > current_time
            )
        ).all()
        
        print(f"📊 Tìm thấy {len(active_accounts)} accounts có token hợp lệ")
        
        if not active_accounts:
            print("❌ Không có account nào có token hợp lệ")
            return
        
        total_emails_synced = 0
        total_receipts_processed = 0
        
        for account in active_accounts:
            try:
                print(f"\n📧 Đang xử lý account {account.id} ({account.email})...")
                
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
        print(f"  - Accounts đã xử lý: {len(active_accounts)}")
        print(f"  - Tổng emails đã sync: {total_emails_synced}")
        print(f"  - Tổng receipts đã xử lý: {total_receipts_processed}")
        
    except Exception as e:
        print(f"❌ Lỗi chung: {str(e)}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành test daily sync!")

if __name__ == "__main__":
    test_daily_sync() 