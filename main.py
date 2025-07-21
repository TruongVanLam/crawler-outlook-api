from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import requests
import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Optional
from sqlalchemy.orm import Session

# Import database và models
from database import get_db, create_tables, engine
from models import Account, AuthToken, Email, EmailAttachment
from crud import (
    save_user_and_token_to_db, 
    get_account_by_email, 
    get_account_by_id,
    get_valid_auth_token,
    create_email,
    get_emails,
    get_email_by_message_id,
    search_emails,
    update_auth_token
)

app = FastAPI()

CLIENT_ID = "b6239e39-c5f9-4704-ac0d-bcb0e0dc87b6"
CLIENT_SECRET = "cOb8Q~KsEr2B.UpGCBxp5Sqcs6JnBs~Osc_~fa4B"
REDIRECT_URI = "http://localhost:8000/auth/callback"
AUTHORITY = "https://login.microsoftonline.com/consumers"  # Cho tài khoản cá nhân
SCOPE = ["offline_access", "Mail.Read"]  # offline_access để lấy refresh_token
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

def refresh_access_token(db: Session, account_id: int):
    """Refresh access token khi hết hạn"""
    auth_token = get_valid_auth_token(db, account_id)
    if not auth_token:
        raise HTTPException(status_code=401, detail="No valid token found")
    
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "scope": " ".join(SCOPE),
        "refresh_token": auth_token.refresh_token,
        "grant_type": "refresh_token",
        "client_secret": CLIENT_SECRET
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to refresh token")
    
    token_data = response.json()
    
    # Cập nhật token trong database
    update_auth_token(db, auth_token.id, 
                     access_token=token_data['access_token'],
                     refresh_token=token_data['refresh_token'],
                     expires_in=token_data['expires_in'],
                     expires_at=datetime.utcnow() + timedelta(seconds=token_data['expires_in']))
    
    return token_data['access_token']

def get_valid_access_token(db: Session, account_id: int):
    """Lấy access token hợp lệ"""
    auth_token = get_valid_auth_token(db, account_id)
    
    if not auth_token:
        raise HTTPException(status_code=401, detail="No access token available")
    
    # Kiểm tra xem token có hết hạn không
    if datetime.utcnow() >= auth_token.expires_at:
        return refresh_access_token(db, account_id)
    
    return auth_token.access_token

@app.get("/login")
def login():
    """
    Tạo URL để user đăng nhập Microsoft
    """
    query_params = urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:8000/auth/callback",
        "response_mode": "query",
        "scope": "offline_access Mail.Read User.Read"
    })
    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query_params}"
    
    return JSONResponse({
        "login_url": auth_url,
        "message": "Truy cập URL này để đăng nhập Microsoft"
    })

@app.get("/auth/callback")
def callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    data = {
        "client_id": CLIENT_ID,
        "scope": "offline_access Mail.Read User.Read",
        "code": code,
        "redirect_uri": "http://localhost:8000/auth/callback",
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
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    if me_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    me = me_response.json()
    email = me["userPrincipalName"]
    name = me.get("displayName", "")

    # Lưu vào database
    account, auth_token = save_user_and_token_to_db(
        db, email, name, access_token, refresh_token, expires_in, me
    )
    
    return {"message": "Thêm tài khoản thành công!", "email": email, "account_id": account.id}


@app.get("/mails")
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
    - account_id: ID của tài khoản
    - top: Số lượng email tối đa (mặc định 10)
    - skip: Số email bỏ qua (cho phân trang)
    - is_read: Lọc theo trạng thái đọc
    - has_attachments: Lọc theo có file đính kèm
    - subject_filter: Lọc theo tiêu đề (ví dụ: "Your Meta ads receipt")
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

@app.get("/mails/{message_id}")
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

@app.get("/mails/sync/")
def sync_emails(
    account_id: int,
    top: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ email từ Microsoft Graph API vào database
    Chỉ lấy email có tiêu đề bắt đầu bằng 'Your Meta ads receipt' hoặc 'Biên lai quảng cáo Meta của bạn'
    """
    print(f"🔍 DEBUG: sync_emails called with account_id={account_id}, top={top}")
    
    try:
        print(f"🔍 DEBUG: Getting access token for account_id={account_id}")
        # Lấy access token
        access_token = get_valid_access_token(db, account_id)
        print(f"🔍 DEBUG: Got access token successfully")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Gọi Microsoft Graph API để lấy emails với filter theo tiêu đề
        params = {
            "$top": top,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,sentDateTime,isRead,hasAttachments,body,bodyPreview,importance,conversationId,conversationIndex,flag,categories,attachments",
            # "$filter": "startswith(subject, 'Your Meta ads receipt') or startswith(subject, 'Biên lai quảng cáo Meta của bạn')"
        }
        
        response = requests.get(
            f"{GRAPH_API_BASE}/me/messages",
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.text, detail="Failed to fetch emails from Microsoft Graph")
        
        emails_data = response.json()
        synced_count = 0
        
        # Lưu từng email vào database
        for email_data in emails_data.get("value", []):
            email_id = email_data.get("id")
            # Kiểm tra xem email đã tồn tại trong db chưa
            existing_email = db.query(Email).filter_by(account_id=account_id, message_id=email_id).first()
            if existing_email:
                print(f"⚠️ Email already exists in DB: {email_data.get('subject', 'No subject')} (id: {email_id})")
                continue
            try:
                subject = email_data.get("subject", "")
                if subject.startswith("Your Meta ads receipt") or subject.startswith("Biên lai quảng cáo Meta của bạn"):
                    create_email(db, account_id, email_data)
                    synced_count += 1
                    print(f"✅ Synced email: {subject if subject else 'No subject'}")
            except Exception as e:
                print(f"Error saving email {email_id}: {str(e)}")
                continue
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {synced_count} email Meta ads receipt",
            "synced_count": synced_count,
            "total_fetched": len(emails_data.get("value", [])),
            "filter": "Meta ads receipt emails only"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mails/sync-all/")
def sync_all_emails(
    account_id: int,
    top: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """
    Đồng bộ tất cả email từ Microsoft Graph API vào database (không filter)
    """
    print(f"🔍 DEBUG: sync_all_emails called with account_id={account_id}, top={top}")
    
    try:
        print(f"🔍 DEBUG: Getting access token for account_id={account_id}")
        # Lấy access token
        access_token = get_valid_access_token(db, account_id)
        print(f"🔍 DEBUG: Got access token successfully")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Gọi Microsoft Graph API để lấy tất cả emails
        params = {
            "$top": top,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,sentDateTime,isRead,hasAttachments,body,bodyPreview,importance,conversationId,conversationIndex,flag,categories,attachments"
        }
        
        response = requests.get(
            f"{GRAPH_API_BASE}/me/messages",
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch emails from Microsoft Graph")
        
        emails_data = response.json()
        synced_count = 0
        
        # Lưu từng email vào database
        for email_data in emails_data.get("value", []):
            try:
                create_email(db, account_id, email_data)
                synced_count += 1
            except Exception as e:
                print(f"Error saving email {email_data.get('id')}: {str(e)}")
                continue
        
        return JSONResponse({
            "message": f"Đồng bộ thành công {synced_count} email",
            "synced_count": synced_count,
            "total_fetched": len(emails_data.get("value", [])),
            "filter": "All emails"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mails/unread/")
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

@app.get("/mails/search/")
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

@app.get("/mails/attachments/{message_id}")
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
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch attachments")
        
        attachments = response.json()
        return JSONResponse(attachments)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{account_id}")
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

@app.post("/init-db")
def init_database():
    """
    Khởi tạo database và tạo các bảng
    """
    try:
        # Test kết nối database trước
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
        
        # Tạo bảng
        create_tables()
        
        # Kiểm tra bảng đã được tạo
        with engine.connect() as connection:
            result = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result]
        
        return JSONResponse({
            "message": "Database initialized successfully",
            "tables_created": tables,
            "total_tables": len(tables)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")

@app.get("/accounts")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
