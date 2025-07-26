"""
Business logic services for email synchronization
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from .graph_api import get_emails_from_graph
from .email_utils import is_meta_receipt_email
from .email_utils_bs4 import extract_meta_receipt_info_combined
from crud import create_email
from models import Email


class EmailSyncService:
    """Service class for email synchronization"""
    
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
    
    def sync_emails_by_date_range(
        self, 
        received_from: str = None, 
        received_to: str = None,
        top: int = 999
    ) -> Dict[str, Any]:
        """
        Đồng bộ email theo khoảng thời gian
        """
        try:
            # Lấy emails từ Graph API
            emails_data = get_emails_from_graph(
                self.db, 
                self.account_id, 
                top, 
                received_from, 
                received_to
            )
            
            synced_count = 0
            meta_receipt_rows = []
            
            # Lưu từng email vào database
            for email_data in emails_data.get("value", []):
                email_id = email_data.get("id")
                
                # Kiểm tra email đã tồn tại chưa
                existing_email = self.db.query(Email).filter_by(
                    account_id=self.account_id, 
                    message_id=email_id
                ).first()
                
                if existing_email:
                    print(f"⚠️ Email already exists in DB: {email_data.get('subject', 'No subject')} (id: {email_id})")
                    continue
                
                subject = email_data.get("subject", "")
                
                # Chỉ lưu Meta receipt emails
                if is_meta_receipt_email(subject):
                    # Trích xuất thông tin từ body và body_preview
                    body_html = email_data.get('body', {}).get('content', '')
                    body_preview = email_data.get('bodyPreview', '')
                    meta_info = extract_meta_receipt_info_combined(body_html, body_preview)
                    
                    # Lấy ngày nhận mail
                    received_date = email_data.get('receivedDateTime')
                    meta_info['Date'] = received_date
                    meta_receipt_rows.append({
                        'Date': received_date,
                        'account_id': meta_info.get('account_id'),
                        'transaction_id': meta_info.get('transaction_id'),
                        'payment': meta_info.get('payment'),
                        'card_number': meta_info.get('card_number'),
                        'reference_number': meta_info.get('reference_number')
                    })
                    
                    print(f"[Meta Receipt Info] {meta_info}")
                    create_email(self.db, self.account_id, email_data)
                    synced_count += 1
                    print(f"✅ Synced email: {subject if subject else 'No subject'}")
            
            return {
                "synced_count": synced_count,
                "total_fetched": len(emails_data.get("value", [])),
                "meta_receipt_rows": meta_receipt_rows
            }
            
        except Exception as e:
            print(f"Error in sync_emails_by_date_range: {str(e)}")
            raise
    
    def sync_monthly_emails(self) -> Dict[str, Any]:
        """
        Đồng bộ email trong 1 tháng gần nhất
        """
        today = datetime.utcnow().date()
        one_month_ago = today - timedelta(days=30)
        total_synced = 0
        total_days = 0
        details = []
        
        for i in range(31):
            day_from = one_month_ago + timedelta(days=i)
            day_to = day_from
            
            if day_from > today:
                break
                
            received_from = day_from.strftime('%Y-%m-%d')
            received_to = day_to.strftime('%Y-%m-%d')
            
            try:
                result = self.sync_emails_by_date_range(received_from, received_to)
                synced_count = result["synced_count"]
                total_synced += synced_count
                total_days += 1
                
                details.append({
                    "date": received_from,
                    "synced": synced_count,
                    "total_fetched": result["total_fetched"]
                })
                
            except Exception as e:
                details.append({
                    "date": received_from,
                    "error": str(e)
                })
                continue
        
        return {
            "total_synced": total_synced,
            "days_processed": total_days,
            "details": details
        }
    
    def sync_daily_emails(self) -> Dict[str, Any]:
        """
        Đồng bộ email mới hàng ngày
        """
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        received_from = yesterday.strftime('%Y-%m-%d')
        received_to = today.strftime('%Y-%m-%d')
        
        try:
            result = self.sync_emails_by_date_range(received_from, received_to)
            
            return {
                "total_synced": result["synced_count"],
                "total_fetched": result["total_fetched"],
                "date_range": {
                    "from": received_from,
                    "to": received_to
                }
            }
            
        except Exception as e:
            raise 