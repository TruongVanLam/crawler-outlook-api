"""
Authentication and token management functions
"""
import requests
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPE
from crud import get_valid_auth_token, update_auth_token


def refresh_access_token(db: Session, account_id: int) -> str:
    """Refresh access token khi hết hạn"""
    try:
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
    except Exception as e:
        print(f"🔍 DEBUG: Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_valid_access_token(db: Session, account_id: int) -> str:
    """Lấy access token hợp lệ"""
    try:
        auth_token = get_valid_auth_token(db, account_id)

        if not auth_token:
            raise HTTPException(status_code=401, detail="No access token available")

        # Kiểm tra xem token có hết hạn không
        if datetime.utcnow() >= auth_token.expires_at:
            return refresh_access_token(db, account_id)

        return auth_token.access_token
    except Exception as e:
        print(f"🔍 DEBUG: Error getting access token: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 