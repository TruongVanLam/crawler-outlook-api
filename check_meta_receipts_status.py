"""
Script để kiểm tra trạng thái của bảng meta_receipts
"""
import sys
import os
from datetime import datetime

# Thêm thư mục hiện tại vào path để import các module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Email, MetaReceipt, Account
from sqlalchemy import func

def check_meta_receipts_status():
    """
    Kiểm tra trạng thái của bảng meta_receipts
    """
    db = SessionLocal()
    
    try:
        print("📊 KIỂM TRA TRẠNG THÁI META_RECEIPTS")
        print("="*50)
        
        # Thống kê tổng quan
        total_emails = db.query(Email).count()
        total_receipts = db.query(MetaReceipt).count()
        
        print(f"📧 Tổng số emails: {total_emails}")
        print(f"📋 Tổng số meta_receipts: {total_receipts}")
        print(f"📈 Tỷ lệ convert: {(total_receipts/total_emails*100):.1f}%" if total_emails > 0 else "N/A")
        
        # Thống kê theo status
        print("\n📈 Thống kê theo status:")
        status_stats = db.query(MetaReceipt.status, func.count(MetaReceipt.id)).group_by(MetaReceipt.status).all()
        for status, count in status_stats:
            percentage = (count/total_receipts*100) if total_receipts > 0 else 0
            print(f"  - {status}: {count} ({percentage:.1f}%)")
        
        # Thống kê theo account
        print("\n📊 Thống kê theo account:")
        account_stats = db.query(
            MetaReceipt.account_id,
            func.count(MetaReceipt.id)
        ).group_by(MetaReceipt.account_id).all()
        
        for account_id, count in account_stats:
            # Lấy thông tin account
            account = db.query(Account).filter(Account.id == account_id).first()
            account_email = account.email if account else f"Account {account_id}"
            
            # Đếm số emails của account này
            account_emails = db.query(Email).filter(Email.account_id == account_id).count()
            convert_rate = (count/account_emails*100) if account_emails > 0 else 0
            
            print(f"  - {account_email} (ID: {account_id}): {count} receipts / {account_emails} emails ({convert_rate:.1f}%)")
        
        # Thống kê theo ngày
        print("\n📅 Thống kê theo ngày (7 ngày gần nhất):")
        from datetime import timedelta
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        recent_receipts = db.query(
            func.date(MetaReceipt.created_at),
            func.count(MetaReceipt.id)
        ).filter(
            MetaReceipt.created_at >= seven_days_ago
        ).group_by(func.date(MetaReceipt.created_at)).order_by(func.date(MetaReceipt.created_at).desc()).all()
        
        for date, count in recent_receipts:
            print(f"  - {date}: {count} receipts")
        
        # Kiểm tra emails chưa được convert
        print("\n🔍 Kiểm tra emails chưa được convert:")
        unconverted_emails = db.query(Email).outerjoin(
            MetaReceipt, 
            (Email.account_id == MetaReceipt.account_id) & (Email.message_id == MetaReceipt.message_id)
        ).filter(MetaReceipt.id.is_(None)).count()
        
        print(f"  - Emails chưa convert: {unconverted_emails}")
        
        if unconverted_emails > 0:
            print(f"  - Cần chạy script convert để xử lý {unconverted_emails} emails còn lại")
        else:
            print("  - ✅ Tất cả emails đã được convert!")
        
        return {
            'total_emails': total_emails,
            'total_receipts': total_receipts,
            'unconverted_emails': unconverted_emails,
            'status_stats': dict(status_stats),
            'account_stats': dict(account_stats)
        }
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None
    
    finally:
        db.close()

def check_account_meta_receipts(account_id: int):
    """
    Kiểm tra chi tiết meta_receipts của một account
    """
    db = SessionLocal()
    
    try:
        print(f"📊 KIỂM TRA META_RECEIPTS CHO ACCOUNT {account_id}")
        print("="*50)
        
        # Lấy thông tin account
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            print(f"❌ Không tìm thấy account {account_id}")
            return None
        
        print(f"📧 Account: {account.email}")
        
        # Thống kê emails
        total_emails = db.query(Email).filter(Email.account_id == account_id).count()
        total_receipts = db.query(MetaReceipt).filter(MetaReceipt.account_id == account_id).count()
        
        print(f"📧 Tổng số emails: {total_emails}")
        print(f"📋 Tổng số meta_receipts: {total_receipts}")
        print(f"📈 Tỷ lệ convert: {(total_receipts/total_emails*100):.1f}%" if total_emails > 0 else "N/A")
        
        # Thống kê theo status
        print("\n📈 Thống kê theo status:")
        status_stats = db.query(MetaReceipt.status, func.count(MetaReceipt.id)).filter(
            MetaReceipt.account_id == account_id
        ).group_by(MetaReceipt.status).all()
        
        for status, count in status_stats:
            percentage = (count/total_receipts*100) if total_receipts > 0 else 0
            print(f"  - {status}: {count} ({percentage:.1f}%)")
        
        # Thống kê theo ngày
        print("\n📅 Thống kê theo ngày (7 ngày gần nhất):")
        from datetime import timedelta
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        recent_receipts = db.query(
            func.date(MetaReceipt.created_at),
            func.count(MetaReceipt.id)
        ).filter(
            MetaReceipt.account_id == account_id,
            MetaReceipt.created_at >= seven_days_ago
        ).group_by(func.date(MetaReceipt.created_at)).order_by(func.date(MetaReceipt.created_at).desc()).all()
        
        for date, count in recent_receipts:
            print(f"  - {date}: {count} receipts")
        
        # Kiểm tra emails chưa được convert
        unconverted_emails = db.query(Email).outerjoin(
            MetaReceipt, 
            (Email.account_id == MetaReceipt.account_id) & (Email.message_id == MetaReceipt.message_id)
        ).filter(
            Email.account_id == account_id,
            MetaReceipt.id.is_(None)
        ).count()
        
        print(f"\n🔍 Emails chưa convert: {unconverted_emails}")
        
        return {
            'account_id': account_id,
            'account_email': account.email,
            'total_emails': total_emails,
            'total_receipts': total_receipts,
            'unconverted_emails': unconverted_emails,
            'status_stats': dict(status_stats)
        }
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None
    
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm tra trạng thái meta_receipts')
    parser.add_argument('--account-id', type=int, help='ID của account cụ thể (nếu không có sẽ kiểm tra tất cả)')
    
    args = parser.parse_args()
    
    if args.account_id:
        result = check_account_meta_receipts(args.account_id)
    else:
        result = check_meta_receipts_status()
    
    if result:
        print("\n✅ Kiểm tra hoàn thành!")
    else:
        print("\n❌ Kiểm tra thất bại!") 