"""
API routes for the application
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import requests
import io
import pandas as pd
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db
from crud import (
    save_user_and_token_to_db, 
    get_account_by_email, 
    get_account_by_id,
    get_valid_auth_token,
    get_emails,
    get_email_by_message_id,
    search_emails,
    # User CRUD
    create_user,
    get_user_by_email,
    verify_user_password,
    get_users,
    update_user,
    delete_user,
    # Account CRUD theo user
    create_account_for_user,
    get_accounts_by_user,
    get_account_by_user_and_id,
    update_account_for_user,
    delete_account_for_user,
    # MetaReceipt CRUD
    get_meta_receipts,
    get_meta_receipts_count
)
from models import Account, User
from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, GRAPH_API_BASE
from .graph_api import get_user_info, get_attachments
from .services import EmailSyncService
from .auth import get_valid_access_token
from .export_service import ExportService
from .meta_receipt_service import MetaReceiptService
from .user_auth import create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# Pydantic models for request/response
class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    email: str
    password: str

class AccountCreate(BaseModel):
    email: str
    name: Optional[str] = None

# User Authentication Endpoints
@router.post("/users/register")
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký user mới"""
    try:
        # Kiểm tra email đã tồn tại chưa
        existing_user = get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        # Tạo user mới
        user = create_user(db, user_data.email, user_data.password, user_data.role)
        
        return JSONResponse({
            "message": "Đăng ký thành công",
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/login")
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập user"""
    try:
        # Xác thực user
        user = verify_user_password(db, user_data.email, user_data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
        
        # Tạo access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User Account Management Endpoints
@router.get("/users/me")
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Lấy thông tin user hiện tại"""
    return JSONResponse({
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    })

@router.get("/users/accounts")
def get_user_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách accounts của user hiện tại"""
    try:
        accounts = get_accounts_by_user(db, current_user.id, skip, limit)
        
        account_list = []
        for account in accounts:
            account_dict = {
                "id": account.id,
                "email": account.email,
                "name": account.name,
                "display_name": account.display_name,
                "is_active": account.is_active,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat()
            }
            account_list.append(account_dict)
        
        return JSONResponse({
            "accounts": account_list,
            "total": len(account_list),
            "user_id": current_user.id
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/accounts")
def create_user_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Tạo account mới cho user hiện tại"""
    try:
        # Kiểm tra email đã tồn tại chưa
        existing_account = get_account_by_email(db, account_data.email)
        if existing_account:
            raise HTTPException(status_code=400, detail="Email account đã tồn tại")
        
        # Tạo account mới
        account = create_account_for_user(
            db, 
            current_user.id, 
            account_data.email, 
            account_data.name
        )
        
        return JSONResponse({
            "message": "Tạo account thành công",
            "account_id": account.id,
            "email": account.email,
            "name": account.name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/accounts/{account_id}")
def get_user_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lấy thông tin chi tiết account của user"""
    try:
        account = get_account_by_user_and_id(db, current_user.id, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account không tồn tại")
        
        account_dict = {
            "id": account.id,
            "email": account.email,
            "name": account.name,
            "display_name": account.display_name,
            "user_principal_name": account.user_principal_name,
            "given_name": account.given_name,
            "surname": account.surname,
            "job_title": account.job_title,
            "office_location": account.office_location,
            "mobile_phone": account.mobile_phone,
            "business_phones": account.business_phones,
            "is_active": account.is_active,
            "created_at": account.created_at.isoformat(),
            "updated_at": account.updated_at.isoformat()
        }
        
        return JSONResponse(account_dict)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/accounts/{account_id}")
def update_user_account(
    account_id: int,
    account_data: AccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cập nhật account của user"""
    try:
        account = update_account_for_user(
            db, 
            current_user.id, 
            account_id, 
            email=account_data.email,
            name=account_data.name
        )
        
        if not account:
            raise HTTPException(status_code=404, detail="Account không tồn tại")
        
        return JSONResponse({
            "message": "Cập nhật account thành công",
            "account_id": account.id,
            "email": account.email,
            "name": account.name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/accounts/{account_id}")
def delete_user_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Xóa account của user"""
    try:
        success = delete_account_for_user(db, current_user.id, account_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Account không tồn tại")
        
        return JSONResponse({
            "message": "Xóa account thành công"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/login")
def login():
    """
    Tạo URL để user đăng nhập Microsoft
    """
    from urllib.parse import urlencode
    
    query_params = urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": "offline_access Mail.Read User.Read"
    })
    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query_params}"
    
    return JSONResponse({
        "login_url": auth_url,
        "message": "Truy cập URL này để đăng nhập Microsoft"
    })


@router.get("/auth/callback")
def callback(code: str, db: Session = Depends(get_db)):
    """
    Callback sau khi user đăng nhập Microsoft
    """
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    data = {
        "client_id": CLIENT_ID,
        "scope": "offline_access Mail.Read User.Read",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(token_url, data=data)
    token_data = response.json()

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]

    # Lấy info user
    me = get_user_info(access_token)
    email = me["userPrincipalName"]
    name = me.get("displayName", "")

    # Lưu vào database
    account, auth_token = save_user_and_token_to_db(
        db, email, name, access_token, refresh_token, expires_in, me
    )
    
    return {"message": "Thêm tài khoản thành công!", "email": email, "account_id": account.id}


@router.get("/mails")
def get_mails(
    account_ids: str,  # Comma-separated list of account IDs
    from_date: Optional[str] = None,  # Format: YYYY-MM-DD
    to_date: Optional[str] = None,    # Format: YYYY-MM-DD
    top: Optional[int] = 20,
    skip: Optional[int] = 0,
    status: Optional[str] = None,  # Filter theo status: Success, Fail, Duplicate, None
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách Meta receipts từ database theo account_ids và khoảng thời gian
    """
    try:
        # Parse account_ids từ string thành list
        account_id_list = [int(id.strip()) for id in account_ids.split(',') if id.strip()]
        
        if not account_id_list:
            raise HTTPException(status_code=400, detail="account_ids không được để trống")
        
        # Kiểm tra quyền truy cập accounts
        user_accounts = get_accounts_by_user(db, current_user.id)
        user_account_ids = [acc.id for acc in user_accounts]
        
        # Kiểm tra xem tất cả account_ids có thuộc về user không
        unauthorized_accounts = [acc_id for acc_id in account_id_list if acc_id not in user_account_ids]
        if unauthorized_accounts:
            raise HTTPException(
                status_code=403, 
                detail=f"Không có quyền truy cập accounts: {unauthorized_accounts}"
            )
        
        # Validate date format nếu có
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng from_date phải là YYYY-MM-DD")
        
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng to_date phải là YYYY-MM-DD")
        
        # Validate status nếu có
        valid_statuses = ['Success', 'Fail', 'Duplicate', 'None']
        if status and status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status phải là một trong: {', '.join(valid_statuses)}")
        
        # Lấy meta receipts từ database
        meta_receipts = get_meta_receipts(
            db, 
            account_id_list, 
            from_date, 
            to_date, 
            skip, 
            top, 
            status
        )
        
        # Đếm tổng số records
        total_count = get_meta_receipts_count(
            db, 
            account_id_list, 
            from_date, 
            to_date, 
            status
        )
        
        # Chuyển đổi thành dict để serialize
        receipts_list = []
        for receipt in meta_receipts:
            receipt_dict = {
                "id": receipt.id,
                "account_id": receipt.account_id,
                "email_id": receipt.email_id,
                "message_id": receipt.message_id,
                "date": receipt.date.isoformat() if receipt.date else None,
                "account_id_meta": receipt.account_id_meta,
                "transaction_id": receipt.transaction_id,
                "payment": receipt.payment,
                "card_number": receipt.card_number,
                "reference_number": receipt.reference_number,
                "status": receipt.status,
                "is_processed": receipt.is_processed,
                "created_at": receipt.created_at.isoformat(),
                "updated_at": receipt.updated_at.isoformat()
            }
            receipts_list.append(receipt_dict)
        
        return JSONResponse({
            "meta_receipts": receipts_list,
            "count": len(receipts_list),
            "total": total_count,
            "skip": skip,
            "top": top,
            "account_ids": account_id_list,
            "from_date": from_date,
            "to_date": to_date,
            "status": status
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/{message_id}")
def get_mail_detail(
    account_id: int,
    message_id: str,
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết một email cụ thể từ database
    """
    try:
        # Lấy email từ database
        email = get_email_by_message_id(db, account_id, message_id)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Chuyển đổi thành dict để serialize
        email_detail = {
            "id": email.id,
            "message_id": email.message_id,
            "subject": email.subject,
            "from": {
                "emailAddress": {
                    "address": email.from_email,
                    "name": email.from_name
                }
            },
            "toRecipients": email.to_recipients,
            "ccRecipients": email.cc_recipients,
            "bccRecipients": email.bcc_recipients,
            "receivedDateTime": email.received_date_time.isoformat() if email.received_date_time else None,
            "sentDateTime": email.sent_date_time.isoformat() if email.sent_date_time else None,
            "isRead": email.is_read,
            "hasAttachments": email.has_attachments,
            "body": {
                "content": email.body,
                "contentType": "html"
            },
            "bodyPreview": email.body_preview,
            "importance": email.importance,
            "conversationId": email.conversation_id,
            "conversationIndex": email.conversation_index,
            "flag": {
                "flagStatus": email.flag_status
            } if email.flag_status else None,
            "categories": email.categories,
            "attachments": email.attachments,
            "created_at": email.created_at.isoformat(),
            "updated_at": email.updated_at.isoformat()
        }
        
        return JSONResponse(email_detail)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/sync/")
def sync_emails(
    account_id: int,
    top: Optional[int] = 50,
    received_from: Optional[str] = None,
    received_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ email từ Microsoft Graph API vào database
    """
    try:
        service = EmailSyncService(db, account_id)
        result = service.sync_emails_by_date_range(received_from, received_to, top)
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {result['synced_count']} email",
            "synced_count": result["synced_count"],
            "total_fetched": result["total_fetched"],
            "filter": f"Meta ads receipt emails from {received_from} to {received_to}" if received_from and received_to else "Meta ads receipt emails only"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/sync-monthly/")
def sync_monthly_emails(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ email trong 1 tháng gần nhất
    """
    try:
        service = EmailSyncService(db, account_id)
        result = service.sync_monthly_emails()
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {result['total_synced']} email trong {result['days_processed']} ngày",
            "total_synced": result["total_synced"],
            "days_processed": result["days_processed"],
            "details": result["details"]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/sync-daily/")
def sync_daily_emails(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ email mới hàng ngày
    """
    try:
        service = EmailSyncService(db, account_id)
        result = service.sync_daily_emails()
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {result['total_synced']} email mới",
            "total_synced": result["total_synced"],
            "total_fetched": result["total_fetched"],
            "date_range": result["date_range"]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/sync-all/")
def sync_all_emails(
    account_id: int,
    top: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ tất cả email từ Microsoft Graph API vào database (không filter)
    """
    try:
        service = EmailSyncService(db, account_id)
        result = service.sync_emails_by_date_range(top=top)
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {result['synced_count']} email",
            "synced_count": result["synced_count"],
            "total_fetched": result["total_fetched"],
            "filter": "All emails"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mails/process-meta-receipts/")
def process_meta_receipts(
    account_ids: str,  # Comma-separated list of account IDs
    from_date: Optional[str] = None,  # Format: YYYY-MM-DD
    to_date: Optional[str] = None,    # Format: YYYY-MM-DD
    limit: Optional[int] = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Xử lý emails và tạo Meta receipts cho các accounts
    """
    try:
        # Parse account_ids từ string thành list
        account_id_list = [int(id.strip()) for id in account_ids.split(',') if id.strip()]
        
        if not account_id_list:
            raise HTTPException(status_code=400, detail="account_ids không được để trống")
        
        # Kiểm tra quyền truy cập accounts
        user_accounts = get_accounts_by_user(db, current_user.id)
        user_account_ids = [acc.id for acc in user_accounts]
        
        # Kiểm tra xem tất cả account_ids có thuộc về user không
        unauthorized_accounts = [acc_id for acc_id in account_id_list if acc_id not in user_account_ids]
        if unauthorized_accounts:
            raise HTTPException(
                status_code=403, 
                detail=f"Không có quyền truy cập accounts: {unauthorized_accounts}"
            )
        
        # Validate date format nếu có
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng from_date phải là YYYY-MM-DD")
        
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng to_date phải là YYYY-MM-DD")
        
        # Xử lý Meta receipts
        service = MetaReceiptService(db)
        results = service.process_multiple_accounts(account_id_list, from_date, to_date, limit)
        
        return JSONResponse({
            "message": "Xử lý Meta receipts thành công",
            "results": results,
            "account_ids": account_id_list,
            "from_date": from_date,
            "to_date": to_date
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mails/reprocess-failed-receipts/")
def reprocess_failed_receipts(
    account_ids: str,  # Comma-separated list of account IDs
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Xử lý lại các Meta receipts có status 'Fail' hoặc 'None'
    """
    try:
        # Parse account_ids từ string thành list
        account_id_list = [int(id.strip()) for id in account_ids.split(',') if id.strip()]
        
        if not account_id_list:
            raise HTTPException(status_code=400, detail="account_ids không được để trống")
        
        # Kiểm tra quyền truy cập accounts
        user_accounts = get_accounts_by_user(db, current_user.id)
        user_account_ids = [acc.id for acc in user_accounts]
        
        # Kiểm tra xem tất cả account_ids có thuộc về user không
        unauthorized_accounts = [acc_id for acc_id in account_id_list if acc_id not in user_account_ids]
        if unauthorized_accounts:
            raise HTTPException(
                status_code=403, 
                detail=f"Không có quyền truy cập accounts: {unauthorized_accounts}"
            )
        
        # Xử lý lại failed receipts
        service = MetaReceiptService(db)
        results = []
        
        for account_id in account_id_list:
            result = service.reprocess_failed_receipts(account_id)
            result['account_id'] = account_id
            results.append(result)
        
        return JSONResponse({
            "message": "Xử lý lại failed receipts thành công",
            "results": results,
            "account_ids": account_id_list
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/search/")
def search_mails(
    account_id: int,
    query: str,
    top: Optional[int] = 10,
    skip: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm email theo từ khóa trong database
    """
    try:
        # Tìm kiếm trong database
        emails = search_emails(db, account_id, query, skip, top)
        
        # Chuyển đổi thành dict để serialize
        email_list = []
        for email in emails:
            email_dict = {
                "id": email.id,
                "message_id": email.message_id,
                "subject": email.subject,
                "from": {
                    "emailAddress": {
                        "address": email.from_email,
                        "name": email.from_name
                    }
                },
                "receivedDateTime": email.received_date_time.isoformat() if email.received_date_time else None,
                "isRead": email.is_read,
                "hasAttachments": email.has_attachments,
                "bodyPreview": email.body_preview,
                "importance": email.importance,
                "created_at": email.created_at.isoformat(),
                "updated_at": email.updated_at.isoformat()
            }
            email_list.append(email_dict)
        
        return JSONResponse({
            "emails": email_list,
            "total": len(email_list),
            "query": query,
            "skip": skip,
            "top": top
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mails/attachments/{message_id}")
def get_mail_attachments(
    account_id: int,
    message_id: str,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách file đính kèm của một email
    """
    try:
        access_token = get_valid_access_token(db, account_id)
        attachments = get_attachments(access_token, message_id)
        return JSONResponse(attachments)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{account_id}")
def get_auth_status(account_id: int, db: Session = Depends(get_db)):
    """
    Kiểm tra trạng thái xác thực của account
    """
    try:
        # Kiểm tra account có tồn tại không
        account = get_account_by_id(db, account_id)
        if not account:
            return JSONResponse({"authenticated": False, "message": "Account not found"})
        
        # Kiểm tra token có hợp lệ không
        auth_token = get_valid_auth_token(db, account_id)
        if not auth_token:
            return JSONResponse({"authenticated": False, "message": "No valid token found"})
        
        return JSONResponse({
            "authenticated": True,
            "account": {
                "id": account.id,
                "email": account.email,
                "name": account.name,
                "display_name": account.display_name
            },
            "token": {
                "expires_at": auth_token.expires_at.isoformat(),
                "expires_in": auth_token.expires_in,
                "is_active": auth_token.is_active
            },
            "message": "Token is valid"
        })
        
    except Exception as e:
        return JSONResponse({"authenticated": False, "message": str(e)})


@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả accounts
    """
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        account_list = []
        for account in accounts:
            account_dict = {
                "id": account.id,
                "email": account.email,
                "name": account.name,
                "display_name": account.display_name,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat()
            }
            account_list.append(account_dict)
        
        return JSONResponse({"accounts": account_list, "total": len(account_list)})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 


@router.get("/export/meta-receipts/")
def export_meta_receipts(
    account_ids: str,  # Comma-separated list of account IDs
    from_date: str,    # Format: YYYY-MM-DD
    to_date: str,      # Format: YYYY-MM-DD
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Xuất Meta receipts theo account_ids và khoảng thời gian
    Trả về file ZIP chứa các file Excel riêng cho từng account
    """
    try:
        # Parse account_ids từ string thành list
        account_id_list = [int(id.strip()) for id in account_ids.split(',') if id.strip()]
        
        if not account_id_list:
            raise HTTPException(status_code=400, detail="account_ids không được để trống")
        
        # Kiểm tra quyền truy cập accounts
        user_accounts = get_accounts_by_user(db, current_user.id)
        user_account_ids = [acc.id for acc in user_accounts]
        
        # Kiểm tra xem tất cả account_ids có thuộc về user không
        unauthorized_accounts = [acc_id for acc_id in account_id_list if acc_id not in user_account_ids]
        if unauthorized_accounts:
            raise HTTPException(
                status_code=403, 
                detail=f"Không có quyền truy cập accounts: {unauthorized_accounts}"
            )
        
        # Validate date format
        try:
            datetime.strptime(from_date, '%Y-%m-%d')
            datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Định dạng ngày phải là YYYY-MM-DD")
        
        # Tạo export service
        export_service = ExportService(db)
        
        # Xuất data và tạo ZIP file
        zip_buffer = export_service.export_meta_receipts(account_id_list, from_date, to_date)
        
        # Tạo tên file ZIP
        zip_filename = f"meta_receipts_{from_date}_{to_date}.zip"
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 