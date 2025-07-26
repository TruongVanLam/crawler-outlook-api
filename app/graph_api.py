"""
Microsoft Graph API functions
"""
import requests
from typing import Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .config import GRAPH_API_BASE
from .auth import get_valid_access_token
from .email_utils import build_email_filter, get_email_api_params


def get_emails_from_graph(
    db: Session, 
    account_id: int, 
    top: int = 999,
    received_from: str = None,
    received_to: str = None
) -> Dict[str, Any]:
    """
    Lấy emails từ Microsoft Graph API
    """
    try:
        access_token = get_valid_access_token(db, account_id)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Build filter và parameters
        filter_str = build_email_filter(received_from, received_to)
        params = get_email_api_params(top, filter_str)
        
        response = requests.get(
            f"{GRAPH_API_BASE}/me/messages",
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Failed to fetch emails from Microsoft Graph: {response.text}"
            )
        
        return response.json()
        
    except Exception as e:
        print(f"🔍 DEBUG: Error fetching emails from Graph API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Lấy thông tin user từ Microsoft Graph API
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{GRAPH_API_BASE}/me", headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to get user info"
        )
    
    return response.json()


def get_attachments(access_token: str, message_id: str) -> Dict[str, Any]:
    """
    Lấy attachments của một email
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments",
        headers=headers
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to fetch attachments"
        )
    
    return response.json() 