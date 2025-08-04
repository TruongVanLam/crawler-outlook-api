"""
Configuration settings for the application
"""
import os
from typing import List

# Microsoft Graph API Configuration
CLIENT_ID = "b6239e39-c5f9-4704-ac0d-bcb0e0dc87b6"
CLIENT_SECRET = "cOb8Q~KsEr2B.UpGCBxp5Sqcs6JnBs~Osc_~fa4B"
# REDIRECT_URI = "http://localhost:8000/auth/callback"
REDIRECT_URI = "https://exec-reached-boston-alice.trycloudflare.com/api/v1/auth/callback"
AUTHORITY = "https://login.microsoftonline.com/consumers"  # Cho tài khoản cá nhân
SCOPE: List[str] = ["offline_access", "Mail.Read"]  # offline_access để lấy refresh_token
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Email filter patterns
META_RECEIPT_SUBJECTS = [
    "Your Meta ads receipt",
    "Biên lai quảng cáo Meta của bạn",
    "Meta ads receipt",
    "Biên lai Meta"
]

# API limits
MAX_EMAILS_PER_REQUEST = 999 