"""
Script để test daily sync thủ công và kiểm tra auto sync
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

def test_manual_daily_sync():
    """
    Test daily sync thủ công và kiểm tra auto sync
    """
    print("🔄 TEST MANUAL DAILY SYNC")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        current_time = datetime.utcnow()
        print(f"⏰ Thời gian hiện tại: {current_time}")
        
        # Lấy tất cả accounts có token hợp lệ
        accounts = db.query(Account).join(AuthToken).filter(
            and_(
                Account.is_active == True,
                AuthToken.is_active == True,
                AuthToken.expires_at > current_time
            )
        ).all()
        
        print(f"📊 Tìm thấy {len(accounts)} accounts có token hợp lệ")
        
        if not accounts:
            print("❌ Không có account nào có token hợp lệ")
            return
        
        total_emails_synced = 0
        total_receipts_processed = 0
        
        for account in accounts:
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
                    meta_result = meta_service.process_account(account.id)
                    
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
        print(f"  - Tổng emails đã sync: {total_emails_synced}")
        print(f"  - Tổng receipts đã xử lý: {total_receipts_processed}")
        
        # Kiểm tra auto sync service
        print(f"\n🔍 KIỂM TRA AUTO SYNC SERVICE:")
        try:
            import requests
            response = requests.get("http://localhost:8000/api/v1/auto-sync/status")
            if response.status_code == 200:
                status = response.json()
                print(f"  - Auto sync đang chạy: {status['status']['is_running']}")
                print(f"  - Sync interval: {status['status']['sync_interval']} giây")
                print(f"  - Số account mới: {status['status']['new_accounts_count']}")
            else:
                print(f"  - ❌ Không thể kết nối đến API server")
        except Exception as e:
            print(f"  - ❌ Lỗi khi kiểm tra auto sync: {str(e)}")
        
    except Exception as e:
        print(f"❌ Lỗi chung: {str(e)}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành test manual daily sync!")

if __name__ == "__main__":
    test_manual_daily_sync() 