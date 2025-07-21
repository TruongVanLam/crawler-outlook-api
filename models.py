from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Import Base từ database.py
from database import Base

class Account(Base):
    """Model cho bảng accounts - lưu thông tin tài khoản người dùng"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    user_principal_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    given_name = Column(String(255), nullable=True)
    surname = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    office_location = Column(String(255), nullable=True)
    mobile_phone = Column(String(50), nullable=True)
    business_phones = Column(JSON, nullable=True)  # Lưu dạng array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship với auth_tokens
    auth_tokens = relationship("AuthToken", back_populates="account", cascade="all, delete-orphan")
    
    # Relationship với emails
    emails = relationship("Email", back_populates="account", cascade="all, delete-orphan")

class AuthToken(Base):
    """Model cho bảng auth_tokens - lưu thông tin token xác thực"""
    __tablename__ = "auth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="Bearer")
    expires_in = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    scope = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship với account
    account = relationship("Account", back_populates="auth_tokens")

class Email(Base):
    """Model cho bảng emails - lưu thông tin email"""
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    message_id = Column(String(500), unique=True, index=True, nullable=False)  # ID từ Microsoft Graph
    subject = Column(String(1000), nullable=True)
    from_email = Column(String(255), nullable=True)
    from_name = Column(String(255), nullable=True)
    to_recipients = Column(JSON, nullable=True)  # Lưu dạng array of objects
    cc_recipients = Column(JSON, nullable=True)  # Lưu dạng array of objects
    bcc_recipients = Column(JSON, nullable=True)  # Lưu dạng array of objects
    received_date_time = Column(DateTime, nullable=True)
    sent_date_time = Column(DateTime, nullable=True)
    is_read = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    body = Column(Text, nullable=True)
    body_preview = Column(Text, nullable=True)
    importance = Column(String(50), nullable=True)  # low, normal, high
    conversation_id = Column(String(500), nullable=True)
    conversation_index = Column(String(500), nullable=True)
    flag_status = Column(String(50), nullable=True)  # notFlagged, flagged, completed
    categories = Column(JSON, nullable=True)  # Lưu dạng array
    attachments = Column(JSON, nullable=True)  # Lưu dạng array of objects
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship với account
    account = relationship("Account", back_populates="emails")

class EmailAttachment(Base):
    """Model cho bảng email_attachments - lưu thông tin file đính kèm"""
    __tablename__ = "email_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    attachment_id = Column(String(500), nullable=False)  # ID từ Microsoft Graph
    name = Column(String(500), nullable=True)
    content_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)
    is_inline = Column(Boolean, default=False)
    content_id = Column(String(255), nullable=True)
    content_location = Column(String(500), nullable=True)
    content_bytes = Column(Text, nullable=True)  # Base64 encoded content
    file_path = Column(String(1000), nullable=True)  # Đường dẫn file đã tải về
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship với email
    email = relationship("Email") 