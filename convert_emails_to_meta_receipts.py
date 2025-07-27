"""
Script để convert tất cả records từ bảng emails sang bảng meta_receipts
"""
import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Thêm thư mục hiện tại vào path để import các module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Email, MetaReceipt
from app.email_utils_bs4 import extract_meta_receipt_info_combined
from crud import get_meta_receipt_by_message_id, bulk_create_meta_receipts

def convert_emails_to_meta_receipts(batch_size: int = 1000):
    """
    Convert tất cả emails sang meta_receipts theo batch
    """
    db = SessionLocal()
    
    try:
        print("🔄 Bắt đầu convert emails sang meta_receipts...")
        
        # Đếm tổng số emails
        total_emails = db.query(Email).count()
        print(f"📊 Tổng số emails cần xử lý: {total_emails}")
        
        # Đếm số meta_receipts đã có
        existing_receipts = db.query(MetaReceipt).count()
        print(f"📊 Số meta_receipts đã có: {existing_receipts}")
        
        processed_count = 0
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Xử lý theo batch
        offset = 0
        
        while True:
            # Lấy batch emails
            emails = db.query(Email).offset(offset).limit(batch_size).all()
            
            if not emails:
                break
            
            print(f"🔄 Đang xử lý batch {offset//batch_size + 1} ({len(emails)} emails)...")
            
            meta_receipts_data = []
            
            for email in emails:
                processed_count += 1
                
                try:
                    # Kiểm tra xem đã có meta receipt cho email này chưa
                    existing_receipt = get_meta_receipt_by_message_id(db, email.account_id, email.message_id)
                    if existing_receipt:
                        skipped_count += 1
                        continue
                    
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
                    
                    meta_receipts_data.append(meta_receipt_data)
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Lỗi khi xử lý email {email.message_id}: {e}")
                    continue
            
            # Bulk create meta receipts cho batch này
            if meta_receipts_data:
                try:
                    bulk_create_meta_receipts(db, meta_receipts_data)
                    print(f"✅ Đã tạo {len(meta_receipts_data)} meta receipts cho batch này")
                except Exception as e:
                    print(f"❌ Lỗi khi bulk create meta receipts: {e}")
                    # Fallback: tạo từng cái một
                    for data in meta_receipts_data:
                        try:
                            from crud import create_meta_receipt
                            create_meta_receipt(db, **data)
                        except Exception as e2:
                            print(f"❌ Lỗi khi tạo meta receipt: {e2}")
                            error_count += 1
            
            offset += batch_size
            
            # In progress
            progress = (processed_count / total_emails) * 100
            print(f"📈 Tiến độ: {progress:.1f}% ({processed_count}/{total_emails})")
        
        # In kết quả cuối cùng
        print("\n" + "="*50)
        print("🎉 HOÀN THÀNH CONVERT EMAILS SANG META_RECEIPTS")
        print("="*50)
        print(f"📊 Tổng số emails đã xử lý: {processed_count}")
        print(f"✅ Số meta_receipts đã tạo: {created_count}")
        print(f"⏭️ Số emails đã bỏ qua (đã có): {skipped_count}")
        print(f"❌ Số lỗi: {error_count}")
        
        # Đếm tổng số meta_receipts sau khi convert
        final_receipts = db.query(MetaReceipt).count()
        print(f"📊 Tổng số meta_receipts trong database: {final_receipts}")
        
        # Thống kê theo status
        from sqlalchemy import func
        status_stats = db.query(MetaReceipt.status, func.count(MetaReceipt.id)).group_by(MetaReceipt.status).all()
        print("\n📈 Thống kê theo status:")
        for status, count in status_stats:
            print(f"  - {status}: {count}")
        
        return {
            'processed_count': processed_count,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'total_receipts': final_receipts
        }
        
    except Exception as e:
        print(f"❌ Lỗi chung: {e}")
        return None
    
    finally:
        db.close()

def convert_specific_account_emails(account_id: int, batch_size: int = 1000):
    """
    Convert emails của một account cụ thể
    """
    db = SessionLocal()
    
    try:
        print(f"🔄 Bắt đầu convert emails cho account {account_id}...")
        
        # Đếm số emails của account
        total_emails = db.query(Email).filter(Email.account_id == account_id).count()
        print(f"📊 Tổng số emails của account {account_id}: {total_emails}")
        
        processed_count = 0
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Xử lý theo batch
        offset = 0
        
        while True:
            # Lấy batch emails của account
            emails = db.query(Email).filter(Email.account_id == account_id).offset(offset).limit(batch_size).all()
            
            if not emails:
                break
            
            print(f"🔄 Đang xử lý batch {offset//batch_size + 1} ({len(emails)} emails)...")
            
            meta_receipts_data = []
            
            for email in emails:
                processed_count += 1
                
                try:
                    # Kiểm tra xem đã có meta receipt cho email này chưa
                    existing_receipt = get_meta_receipt_by_message_id(db, email.account_id, email.message_id)
                    if existing_receipt:
                        skipped_count += 1
                        continue
                    
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
                    
                    meta_receipts_data.append(meta_receipt_data)
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Lỗi khi xử lý email {email.message_id}: {e}")
                    continue
            
            # Bulk create meta receipts cho batch này
            if meta_receipts_data:
                try:
                    bulk_create_meta_receipts(db, meta_receipts_data)
                    print(f"✅ Đã tạo {len(meta_receipts_data)} meta receipts cho batch này")
                except Exception as e:
                    print(f"❌ Lỗi khi bulk create meta receipts: {e}")
                    # Fallback: tạo từng cái một
                    for data in meta_receipts_data:
                        try:
                            from crud import create_meta_receipt
                            create_meta_receipt(db, **data)
                        except Exception as e2:
                            print(f"❌ Lỗi khi tạo meta receipt: {e2}")
                            error_count += 1
            
            offset += batch_size
            
            # In progress
            progress = (processed_count / total_emails) * 100
            print(f"📈 Tiến độ: {progress:.1f}% ({processed_count}/{total_emails})")
        
        # In kết quả cuối cùng
        print(f"\n🎉 HOÀN THÀNH CONVERT EMAILS CHO ACCOUNT {account_id}")
        print(f"📊 Tổng số emails đã xử lý: {processed_count}")
        print(f"✅ Số meta_receipts đã tạo: {created_count}")
        print(f"⏭️ Số emails đã bỏ qua (đã có): {skipped_count}")
        print(f"❌ Số lỗi: {error_count}")
        
        return {
            'account_id': account_id,
            'processed_count': processed_count,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count
        }
        
    except Exception as e:
        print(f"❌ Lỗi chung: {e}")
        return None
    
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert emails sang meta_receipts')
    parser.add_argument('--account-id', type=int, help='ID của account cụ thể (nếu không có sẽ convert tất cả)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Kích thước batch (mặc định: 1000)')
    
    args = parser.parse_args()
    
    if args.account_id:
        print(f"🎯 Convert emails cho account {args.account_id}")
        result = convert_specific_account_emails(args.account_id, args.batch_size)
    else:
        print("🎯 Convert tất cả emails")
        result = convert_emails_to_meta_receipts(args.batch_size)
    
    if result:
        print("\n✅ Convert thành công!")
    else:
        print("\n❌ Convert thất bại!") 