"""
Service để xử lý Meta receipts - lọc thông tin từ emails và lưu vào bảng meta_receipts
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from models import Email, MetaReceipt
from .email_utils_bs4 import extract_meta_receipt_info_combined
from crud import (
    get_emails, 
    create_meta_receipt, 
    get_meta_receipt_by_message_id,
    bulk_create_meta_receipts
)

logger = logging.getLogger(__name__)

class MetaReceiptService:
    """Service để xử lý Meta receipts"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_email_to_meta_receipt(self, email: Email) -> Dict[str, Any]:
        """
        Xử lý một email và trích xuất thông tin Meta receipt
        """
        try:
            # Trích xuất thông tin từ body và body_preview
            body_html = email.body or ""
            body_preview = email.body_preview or ""
            meta_info = extract_meta_receipt_info_combined(body_html, body_preview)
            
            transaction_id = meta_info.get('transaction_id')
            
            # Kiểm tra xem có text "failed" trong body không
            body_text = (body_html + " " + body_preview).lower()
            if "failed" in body_text:
                status = 'Fail'
            else:
                # Kiểm tra xem transaction_id đã tồn tại trong database chưa
                existing_receipt = get_meta_receipt_by_message_id(self.db, email.account_id, email.message_id)
                if existing_receipt:
                    status = 'Duplicate'
                elif meta_info.get('reference_number') == '':
                    status = 'None'
                else:
                    status = 'Success'
            
            # Tạo data cho meta receipt
            meta_receipt_data = {
                'account_id': email.account_id,
                'email_id': email.id,
                'message_id': email.message_id,
                'date': email.received_date_time,
                'account_id_meta': meta_info.get('account_id'),
                'transaction_id': transaction_id,
                'payment': meta_info.get('payment'),
                'card_number': meta_info.get('card_number'),
                'reference_number': meta_info.get('reference_number'),
                'status': status
            }
            
            return meta_receipt_data
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý email {email.message_id}: {e}")
            return None
    
    def process_emails_batch(self, account_id: int, emails: List[Email]) -> Dict[str, int]:
        """
        Xử lý một batch emails và lưu vào bảng meta_receipts
        """
        processed_count = 0
        created_count = 0
        skipped_count = 0
        
        meta_receipts_data = []
        
        for email in emails:
            processed_count += 1
            
            # Kiểm tra xem đã có meta receipt cho email này chưa
            existing_receipt = get_meta_receipt_by_message_id(self.db, account_id, email.message_id)
            if existing_receipt:
                skipped_count += 1
                continue
            
            # Xử lý email
            meta_receipt_data = self.process_email_to_meta_receipt(email)
            if meta_receipt_data:
                meta_receipts_data.append(meta_receipt_data)
                created_count += 1
        
        # Bulk create meta receipts
        if meta_receipts_data:
            try:
                bulk_create_meta_receipts(self.db, meta_receipts_data)
                logger.info(f"Đã tạo {len(meta_receipts_data)} meta receipts cho account {account_id}")
            except Exception as e:
                logger.error(f"Lỗi khi bulk create meta receipts: {e}")
                # Fallback: tạo từng cái một
                for data in meta_receipts_data:
                    try:
                        create_meta_receipt(self.db, **data)
                    except Exception as e2:
                        logger.error(f"Lỗi khi tạo meta receipt: {e2}")
        
        return {
            'processed_count': processed_count,
            'created_count': created_count,
            'skipped_count': skipped_count
        }
    
    def process_account_emails(
        self, 
        account_id: int, 
        from_date: str = None, 
        to_date: str = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Xử lý tất cả emails của một account và tạo meta receipts
        """
        try:
            # Lấy emails từ database
            emails = get_emails(self.db, account_id, skip=0, limit=limit)
            
            # Filter theo date range nếu có
            if from_date or to_date:
                filtered_emails = []
                for email in emails:
                    if email.received_date_time:
                        email_date = email.received_date_time.date()
                        
                        # Kiểm tra from_date
                        if from_date:
                            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                            if email_date < from_date_obj:
                                continue
                        
                        # Kiểm tra to_date
                        if to_date:
                            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                            if email_date > to_date_obj:
                                continue
                        
                        filtered_emails.append(email)
                emails = filtered_emails
            
            # Xử lý emails
            result = self.process_emails_batch(account_id, emails)
            
            return {
                'account_id': account_id,
                'total_emails': len(emails),
                'processed_count': result['processed_count'],
                'created_count': result['created_count'],
                'skipped_count': result['skipped_count'],
                'from_date': from_date,
                'to_date': to_date
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý emails cho account {account_id}: {e}")
            return {
                'account_id': account_id,
                'error': str(e)
            }
    
    def process_multiple_accounts(
        self, 
        account_ids: List[int], 
        from_date: str = None, 
        to_date: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Xử lý emails của nhiều accounts
        """
        results = []
        
        for account_id in account_ids:
            result = self.process_account_emails(account_id, from_date, to_date, limit)
            results.append(result)
        
        return results
    
    def reprocess_failed_receipts(self, account_id: int) -> Dict[str, int]:
        """
        Xử lý lại các meta receipts có status 'Fail' hoặc 'None'
        """
        try:
            # Lấy các meta receipts cần xử lý lại
            failed_receipts = self.db.query(MetaReceipt).filter(
                and_(
                    MetaReceipt.account_id == account_id,
                    MetaReceipt.status.in_(['Fail', 'None'])
                )
            ).all()
            
            reprocessed_count = 0
            
            for receipt in failed_receipts:
                # Lấy email gốc
                email = self.db.query(Email).filter(Email.id == receipt.email_id).first()
                if not email:
                    continue
                
                # Xử lý lại email
                meta_receipt_data = self.process_email_to_meta_receipt(email)
                if meta_receipt_data:
                    # Cập nhật receipt hiện tại
                    receipt.date = meta_receipt_data['date']
                    receipt.account_id_meta = meta_receipt_data['account_id_meta']
                    receipt.transaction_id = meta_receipt_data['transaction_id']
                    receipt.payment = meta_receipt_data['payment']
                    receipt.card_number = meta_receipt_data['card_number']
                    receipt.reference_number = meta_receipt_data['reference_number']
                    receipt.status = meta_receipt_data['status']
                    receipt.updated_at = datetime.utcnow()
                    
                    reprocessed_count += 1
            
            self.db.commit()
            
            return {
                'total_failed': len(failed_receipts),
                'reprocessed_count': reprocessed_count
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi reprocess failed receipts cho account {account_id}: {e}")
            return {
                'error': str(e)
            } 