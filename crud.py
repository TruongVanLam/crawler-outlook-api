from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
import json
import bcrypt
from passlib.context import CryptContext

from models import Account, AuthToken, Email, EmailAttachment, User, MetaReceipt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User CRUD operations
def create_user(db: Session, email: str, password: str, role: str = "user"):
    """Tạo user mới"""
    # Hash password
    hashed_password = pwd_context.hash(password)
    
    db_user = User(
        email=email,
        password_hash=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    """Lấy user theo email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    """Lấy user theo ID"""
    return db.query(User).filter(User.id == user_id).first()

def verify_user_password(db: Session, email: str, password: str):
    """Xác thực user password"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if pwd_context.verify(password, user.password_hash):
        return user
    return None

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Lấy danh sách users"""
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, **kwargs):
    """Cập nhật thông tin user"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    """Xóa user"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    db.delete(user)
    db.commit()
    return True

# Account CRUD operations (theo user)
def create_account_for_user(db: Session, user_id: int, email: str, name: str = None, user_info: dict = None):
    """Tạo account cho user cụ thể"""
    db_account = Account(
        email=email,
        name=name,
        user_id=user_id,
        user_principal_name=user_info.get("userPrincipalName") if user_info else None,
        display_name=user_info.get("displayName") if user_info else None,
        given_name=user_info.get("givenName") if user_info else None,
        surname=user_info.get("surname") if user_info else None,
        job_title=user_info.get("jobTitle") if user_info else None,
        office_location=user_info.get("officeLocation") if user_info else None,
        mobile_phone=user_info.get("mobilePhone") if user_info else None,
        business_phones=user_info.get("businessPhones") if user_info else None
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

def get_accounts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Lấy danh sách accounts của user"""
    return db.query(Account).filter(
        Account.user_id == user_id,
        Account.is_active == True
    ).offset(skip).limit(limit).all()

def get_account_by_user_and_id(db: Session, user_id: int, account_id: int):
    """Lấy account theo user_id và account_id"""
    return db.query(Account).filter(
        Account.user_id == user_id,
        Account.id == account_id,
        Account.is_active == True
    ).first()

def update_account_for_user(db: Session, user_id: int, account_id: int, **kwargs):
    """Cập nhật account của user"""
    account = get_account_by_user_and_id(db, user_id, account_id)
    if not account:
        return None
    
    for key, value in kwargs.items():
        if hasattr(account, key):
            setattr(account, key, value)
    
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return account

def delete_account_for_user(db: Session, user_id: int, account_id: int):
    """Xóa account của user (soft delete)"""
    account = get_account_by_user_and_id(db, user_id, account_id)
    if not account:
        return False
    
    account.is_active = False
    account.updated_at = datetime.utcnow()
    db.commit()
    return True

# Account CRUD operations
def create_account(db: Session, email: str, name: str = None, user_info: dict = None):
    """Tạo tài khoản mới"""
    db_account = Account(
        email=email,
        name=name,
        user_principal_name=user_info.get("userPrincipalName") if user_info else None,
        display_name=user_info.get("displayName") if user_info else None,
        given_name=user_info.get("givenName") if user_info else None,
        surname=user_info.get("surname") if user_info else None,
        job_title=user_info.get("jobTitle") if user_info else None,
        office_location=user_info.get("officeLocation") if user_info else None,
        mobile_phone=user_info.get("mobilePhone") if user_info else None,
        business_phones=user_info.get("businessPhones") if user_info else None
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

def get_account_by_email(db: Session, email: str):
    """Lấy tài khoản theo email"""
    return db.query(Account).filter(Account.email == email).first()

def get_account_by_id(db: Session, account_id: int):
    """Lấy tài khoản theo ID"""
    return db.query(Account).filter(Account.id == account_id).first()

def update_account(db: Session, account_id: int, **kwargs):
    """Cập nhật thông tin tài khoản"""
    db_account = get_account_by_id(db, account_id)
    if db_account:
        for key, value in kwargs.items():
            if hasattr(db_account, key):
                setattr(db_account, key, value)
        db_account.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_account)
    return db_account

# AuthToken CRUD operations
def create_auth_token(
    db: Session, 
    account_id: int, 
    access_token: str, 
    refresh_token: str, 
    expires_in: int,
    scope: str = None
):
    """Tạo token mới hoặc cập nhật token cũ"""
    # Kiểm tra xem đã có token cho account này chưa
    existing_token = db.query(AuthToken).filter(
        and_(
            AuthToken.account_id == account_id,
            AuthToken.is_active == True
        )
    ).first()
    
    if existing_token:
        # Cập nhật token cũ
        existing_token.access_token = access_token
        existing_token.refresh_token = refresh_token
        existing_token.expires_in = expires_in
        existing_token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        existing_token.scope = scope
        existing_token.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_token)
        return existing_token
    else:
        # Tạo token mới
        db_token = AuthToken(
            account_id=account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            scope=scope
        )
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        return db_token

def get_valid_auth_token(db: Session, account_id: int):
    """Lấy token mới nhất cho account (dù hết hạn)"""
    return db.query(AuthToken).filter(
        AuthToken.account_id == account_id,
        AuthToken.is_active == True
    ).first()

def update_auth_token(db: Session, token_id: int, **kwargs):
    """Cập nhật thông tin token"""
    db_token = db.query(AuthToken).filter(AuthToken.id == token_id).first()
    if db_token:
        for key, value in kwargs.items():
            if hasattr(db_token, key):
                setattr(db_token, key, value)
        db_token.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_token)
    return db_token

def deactivate_auth_token(db: Session, account_id: int):
    """Vô hiệu hóa token của account"""
    db.query(AuthToken).filter(
        and_(
            AuthToken.account_id == account_id,
            AuthToken.is_active == True
        )
    ).update({"is_active": False, "updated_at": datetime.utcnow()})
    db.commit()

# Email CRUD operations
def create_email(db: Session, account_id: int, email_data: dict):
    """Tạo email mới hoặc cập nhật email cũ"""
    # Kiểm tra xem email đã tồn tại chưa
    existing_email = db.query(Email).filter(
        and_(
            Email.account_id == account_id,
            Email.message_id == email_data.get("id")
        )
    ).first()
    
    if existing_email:
        # Cập nhật email cũ
        for key, value in email_data.items():
            if hasattr(existing_email, key) and key != "id":
                setattr(existing_email, key, value)
        existing_email.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_email)
        return existing_email
    else:
        # Tạo email mới
        db_email = Email(
            account_id=account_id,
            message_id=email_data.get("id"),
            subject=email_data.get("subject"),
            from_email=email_data.get("from", {}).get("emailAddress", {}).get("address"),
            from_name=email_data.get("from", {}).get("emailAddress", {}).get("name"),
            to_recipients=email_data.get("toRecipients"),
            cc_recipients=email_data.get("ccRecipients"),
            bcc_recipients=email_data.get("bccRecipients"),
            received_date_time=datetime.fromisoformat(email_data.get("receivedDateTime").replace("Z", "+00:00")) if email_data.get("receivedDateTime") else None,
            sent_date_time=datetime.fromisoformat(email_data.get("sentDateTime").replace("Z", "+00:00")) if email_data.get("sentDateTime") else None,
            is_read=email_data.get("isRead", False),
            has_attachments=email_data.get("hasAttachments", False),
            body=email_data.get("body", {}).get("content") if email_data.get("body") else None,
            body_preview=email_data.get("bodyPreview"),
            importance=email_data.get("importance"),
            conversation_id=email_data.get("conversationId"),
            conversation_index=email_data.get("conversationIndex"),
            flag_status=email_data.get("flag", {}).get("flagStatus") if email_data.get("flag") else None,
            categories=email_data.get("categories"),
            attachments=email_data.get("attachments")
        )
        db.add(db_email)
        db.commit()
        db.refresh(db_email)
        return db_email

def get_emails(
    db: Session, 
    account_id: int, 
    skip: int = 0, 
    limit: int = 10,
    is_read: Optional[bool] = None,
    has_attachments: Optional[bool] = None,
    subject_filter: Optional[str] = None
):
    """Lấy danh sách email với filter"""
    query = db.query(Email).filter(Email.account_id == account_id)
    
    if is_read is not None:
        query = query.filter(Email.is_read == is_read)
    
    if has_attachments is not None:
        query = query.filter(Email.has_attachments == has_attachments)
    
    if subject_filter:
        # Lọc theo tiêu đề bắt đầu với subject_filter
        query = query.filter(Email.subject.ilike(f"{subject_filter}%"))
    
    return query.order_by(Email.received_date_time.desc()).offset(skip).limit(limit).all()

def get_email_by_message_id(db: Session, account_id: int, message_id: str):
    """Lấy email theo message_id"""
    return db.query(Email).filter(
        and_(
            Email.account_id == account_id,
            Email.message_id == message_id
        )
    ).first()

def search_emails(db: Session, account_id: int, query: str, skip: int = 0, limit: int = 10):
    """Tìm kiếm email theo từ khóa"""
    return db.query(Email).filter(
        and_(
            Email.account_id == account_id,
            or_(
                Email.subject.ilike(f"%{query}%"),
                Email.body_preview.ilike(f"%{query}%"),
                Email.from_name.ilike(f"%{query}%"),
                Email.from_email.ilike(f"%{query}%")
            )
        )
    ).order_by(Email.received_date_time.desc()).offset(skip).limit(limit).all()

def update_email_read_status(db: Session, email_id: int, is_read: bool):
    """Cập nhật trạng thái đọc của email"""
    db_email = db.query(Email).filter(Email.id == email_id).first()
    if db_email:
        db_email.is_read = is_read
        db_email.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_email)
    return db_email

# EmailAttachment CRUD operations
def create_email_attachment(db: Session, email_id: int, attachment_data: dict):
    """Tạo attachment mới"""
    db_attachment = EmailAttachment(
        email_id=email_id,
        attachment_id=attachment_data.get("id"),
        name=attachment_data.get("name"),
        content_type=attachment_data.get("contentType"),
        size=attachment_data.get("size"),
        is_inline=attachment_data.get("isInline", False),
        content_id=attachment_data.get("contentId"),
        content_location=attachment_data.get("contentLocation"),
        content_bytes=attachment_data.get("contentBytes"),
        file_path=attachment_data.get("filePath")
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

def get_email_attachments(db: Session, email_id: int):
    """Lấy danh sách attachment của email"""
    return db.query(EmailAttachment).filter(EmailAttachment.email_id == email_id).all()

# Utility functions
def save_user_and_token_to_db(db: Session, email: str, name: str, access_token: str, refresh_token: str, expires_in: int, user_info: dict = None):
    """Lưu user và token vào database"""
    # Tạo hoặc cập nhật account
    account = get_account_by_email(db, email)
    if not account:
        account = create_account(db, email, name, user_info)
    
    # Tạo hoặc cập nhật token
    auth_token = create_auth_token(db, account.id, access_token, refresh_token, expires_in)
    
    return account, auth_token 

# MetaReceipt CRUD operations
def create_meta_receipt(
    db: Session, 
    account_id: int, 
    email_id: int, 
    message_id: str,
    date: datetime = None,
    account_id_meta: str = None,
    transaction_id: str = None,
    payment: str = None,
    card_number: str = None,
    reference_number: str = None,
    status: str = None
):
    """Tạo meta receipt mới"""
    db_meta_receipt = MetaReceipt(
        account_id=account_id,
        email_id=email_id,
        message_id=message_id,
        date=date,
        account_id_meta=account_id_meta,
        transaction_id=transaction_id,
        payment=payment,
        card_number=card_number,
        reference_number=reference_number,
        status=status
    )
    db.add(db_meta_receipt)
    db.commit()
    db.refresh(db_meta_receipt)
    return db_meta_receipt

def get_meta_receipts(
    db: Session, 
    account_ids: List[int], 
    from_date: str = None, 
    to_date: str = None,
    skip: int = 0, 
    limit: int = 100,
    status: str = None
):
    """Lấy danh sách meta receipts theo điều kiện"""
    query = db.query(MetaReceipt).filter(MetaReceipt.account_id.in_(account_ids))
    
    # Filter theo date range
    if from_date:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
        query = query.filter(MetaReceipt.date >= from_date_obj)
    
    if to_date:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
        query = query.filter(MetaReceipt.date <= to_date_obj)
    
    # Filter theo status
    if status:
        query = query.filter(MetaReceipt.status == status)
    
    # Sắp xếp theo date (mới nhất trước)
    query = query.order_by(MetaReceipt.date.desc())
    
    # Pagination
    query = query.offset(skip).limit(limit)
    
    return query.all()

def get_meta_receipt_by_message_id(db: Session, account_id: int, message_id: str):
    """Lấy meta receipt theo message_id"""
    return db.query(MetaReceipt).filter(
        and_(
            MetaReceipt.account_id == account_id,
            MetaReceipt.message_id == message_id
        )
    ).first()

def update_meta_receipt(db: Session, meta_receipt_id: int, **kwargs):
    """Cập nhật meta receipt"""
    meta_receipt = db.query(MetaReceipt).filter(MetaReceipt.id == meta_receipt_id).first()
    if not meta_receipt:
        return None
    
    for key, value in kwargs.items():
        if hasattr(meta_receipt, key):
            setattr(meta_receipt, key, value)
    
    meta_receipt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(meta_receipt)
    return meta_receipt

def delete_meta_receipt(db: Session, meta_receipt_id: int):
    """Xóa meta receipt"""
    meta_receipt = db.query(MetaReceipt).filter(MetaReceipt.id == meta_receipt_id).first()
    if not meta_receipt:
        return False
    
    db.delete(meta_receipt)
    db.commit()
    return True

def bulk_create_meta_receipts(db: Session, meta_receipts_data: List[dict]):
    """Tạo nhiều meta receipts cùng lúc"""
    meta_receipts = []
    for data in meta_receipts_data:
        meta_receipt = MetaReceipt(**data)
        meta_receipts.append(meta_receipt)
    
    db.add_all(meta_receipts)
    db.commit()
    
    # Refresh tất cả objects
    for meta_receipt in meta_receipts:
        db.refresh(meta_receipt)
    
    return meta_receipts

def get_meta_receipts_count(
    db: Session, 
    account_ids: List[int], 
    from_date: str = None, 
    to_date: str = None,
    status: str = None
):
    """Đếm số lượng meta receipts theo điều kiện"""
    query = db.query(MetaReceipt).filter(MetaReceipt.account_id.in_(account_ids))
    
    # Filter theo date range
    if from_date:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
        query = query.filter(MetaReceipt.date >= from_date_obj)
    
    if to_date:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
        query = query.filter(MetaReceipt.date <= to_date_obj)
    
    # Filter theo status
    if status:
        query = query.filter(MetaReceipt.status == status)
    
    return query.count() 