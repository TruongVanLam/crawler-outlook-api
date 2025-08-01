"""
Script để kiểm tra chi tiết trạng thái auto sync service
"""
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Thêm thư mục hiện tại vào path để import các module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Account, AuthToken, Email, MetaReceipt
from app.auto_sync_service import auto_sync_service

def check_auto_sync_status():
    """
    Kiểm tra chi tiết trạng thái auto sync service
    """
    print("🔍 KIỂM TRA TRẠNG THÁI AUTO SYNC SERVICE")
    print("=" * 50)
    
    # 1. Kiểm tra trạng thái service
    print("\n📊 Trạng thái Auto Sync Service:")
    status = auto_sync_service.get_sync_status()
    print(f"  - Đang chạy: {status['is_running']}")
    print(f"  - Sync interval: {status['sync_interval']} giây")
    print(f"  - Số account mới trong queue: {status['new_accounts_count']}")
    print(f"  - Danh sách account mới: {status['new_accounts']}")
    
    # 2. Kiểm tra database
    db = SessionLocal()
    try:
        print("\n📊 Thống kê Database:")
        
        # Đếm accounts
        total_accounts = db.query(Account).count()
        active_accounts = db.query(Account).filter(Account.is_active == True).count()
        print(f"  - Tổng số accounts: {total_accounts}")
        print(f"  - Số accounts active: {active_accounts}")
        
        # Đếm auth tokens
        total_tokens = db.query(AuthToken).count()
        valid_tokens = db.query(AuthToken).filter(
            and_(
                AuthToken.is_active == True,
                AuthToken.expires_at > datetime.utcnow()
            )
        ).count()
        print(f"  - Tổng số auth tokens: {total_tokens}")
        print(f"  - Số tokens hợp lệ: {valid_tokens}")
        
        # Đếm emails
        total_emails = db.query(Email).count()
        print(f"  - Tổng số emails: {total_emails}")
        
        # Đếm meta receipts
        total_receipts = db.query(MetaReceipt).count()
        print(f"  - Tổng số meta receipts: {total_receipts}")
        
        # 3. Kiểm tra chi tiết accounts
        print("\n📋 Chi tiết Accounts:")
        accounts = db.query(Account).all()
        
        if not accounts:
            print("  - Không có account nào trong database")
        else:
            for account in accounts:
                print(f"\n  📧 Account ID: {account.id}")
                print(f"    - Email: {account.email}")
                print(f"    - Name: {account.name}")
                print(f"    - Active: {account.is_active}")
                print(f"    - User ID: {account.user_id}")
                
                # Kiểm tra auth token
                auth_token = db.query(AuthToken).filter(
                    and_(
                        AuthToken.account_id == account.id,
                        AuthToken.is_active == True,
                        AuthToken.expires_at > datetime.utcnow()
                    )
                ).first()
                
                if auth_token:
                    print(f"    - ✅ Có token hợp lệ (hết hạn: {auth_token.expires_at})")
                    
                    # Đếm emails của account này
                    account_emails = db.query(Email).filter(Email.account_id == account.id).count()
                    print(f"    - 📧 Số emails: {account_emails}")
                    
                    # Đếm meta receipts của account này
                    account_receipts = db.query(MetaReceipt).filter(MetaReceipt.account_id == account.id).count()
                    print(f"    - 📄 Số meta receipts: {account_receipts}")
                    
                    # Kiểm tra email gần nhất
                    latest_email = db.query(Email).filter(Email.account_id == account.id).order_by(Email.received_date_time.desc()).first()
                    if latest_email:
                        print(f"    - 📅 Email gần nhất: {latest_email.received_date_time}")
                else:
                    print(f"    - ❌ Không có token hợp lệ")
        
        # 4. Kiểm tra thời gian
        print(f"\n⏰ Thời gian hiện tại: {datetime.utcnow()}")
        print(f"📅 Ngày hiện tại: {datetime.utcnow().date()}")
        
        # 5. Kiểm tra daily sync
        if hasattr(auto_sync_service, 'last_daily_sync_date'):
            print(f"🔄 Lần daily sync gần nhất: {auto_sync_service.last_daily_sync_date}")
            
            if auto_sync_service.last_daily_sync_date == datetime.utcnow().date():
                print("✅ Daily sync đã chạy hôm nay")
            else:
                print("⏳ Daily sync chưa chạy hôm nay")
        else:
            print("❓ Không thể xác định lần daily sync gần nhất")
        
        # 6. Kiểm tra emails gần đây
        print(f"\n📧 Emails gần đây (7 ngày qua):")
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_emails = db.query(Email).filter(Email.received_date_time >= week_ago).count()
        print(f"  - Số emails trong 7 ngày qua: {recent_emails}")
        
        # 7. Kiểm tra meta receipts gần đây
        print(f"\n📄 Meta receipts gần đây (7 ngày qua):")
        recent_receipts = db.query(MetaReceipt).filter(MetaReceipt.date >= week_ago).count()
        print(f"  - Số meta receipts trong 7 ngày qua: {recent_receipts}")
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra database: {e}")
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("✅ Hoàn thành kiểm tra!")

if __name__ == "__main__":
    check_auto_sync_status() 