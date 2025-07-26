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
from datetime import datetime

from database import get_db
from crud import (
    save_user_and_token_to_db, 
    get_account_by_email, 
    get_account_by_id,
    get_valid_auth_token,
    get_emails,
    get_email_by_message_id,
    search_emails
)
from models import Account
from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, GRAPH_API_BASE
from .graph_api import get_user_info, get_attachments
from .services import EmailSyncService
from .auth import get_valid_access_token
from .export_service import ExportService

router = APIRouter()


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
    account_id: int,
    top: Optional[int] = 10,
    skip: Optional[int] = 0,
    is_read: Optional[bool] = None,
    has_attachments: Optional[bool] = None,
    subject_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách email từ database
    """
    try:
        # Lấy emails từ database
        emails = get_emails(db, account_id, skip, top, is_read, has_attachments)
        
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
            "skip": skip,
            "top": top
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


@router.get("/mails/unread/")
def get_unread_mails(
    account_id: int,
    top: Optional[int] = 10, 
    skip: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách email chưa đọc từ database
    """
    return get_mails(account_id=account_id, top=top, skip=skip, is_read=False, db=db)


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