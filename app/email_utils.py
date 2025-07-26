"""
Email processing utilities
"""
import re
from typing import Dict, Any
from .config import META_RECEIPT_SUBJECTS


def extract_meta_receipt_info(body_html: str) -> Dict[str, Any]:
    """
    Trích xuất thông tin từ body HTML của email Meta receipt.
    """
    meta_info = {}
    
    # Account ID - tìm trong phần "Transaction for"
    account_match = re.search(r'Transaction for</div>\s*<div[^>]*>([^<]+)', body_html)
    if account_match:
        account_text = account_match.group(1).strip()
        # Trích xuất số account ID từ text "Meraki-Linh-T2219-1255380388827210 (1255380388827210)"
        account_id_match = re.search(r'\((\d{10,})\)', account_text)
        if account_id_match:
            meta_info['account_id'] = account_id_match.group(1)
    
    # Transaction ID - tìm trong phần "Transaction ID"
    transaction_match = re.search(r'Transaction ID</div>\s*<div[^>]*>\s*<a[^>]*>([^<]+)</a>', body_html)
    if transaction_match:
        meta_info['transaction_id'] = transaction_match.group(1).strip()
    
    # Payment amount - tìm trong phần "Amount billed"
    payment_match = re.search(r'Amount\s+billed[^<]*</td>\s*</tr>\s*<tr>\s*<td[^>]*>\s*<div[^>]*>\s*\$([\d,]+\.?\d*)\s*USD', body_html, re.IGNORECASE | re.DOTALL)
    if payment_match:
        payment_amount = payment_match.group(1).replace(',', '')
        meta_info['payment'] = payment_amount
    
    # Card number - tìm trong phần "PAYMENT METHOD"
    card_match = re.search(r'PAYMENT\s+METHOD[^<]*</td>\s*</tr>\s*<tr>\s*<td[^>]*>\s*<div[^>]*>([^<]+)', body_html, re.IGNORECASE | re.DOTALL)
    if card_match:
        card_text = card_match.group(1).strip()
        # Trích xuất số thẻ từ text "Visa · 1582"
        card_number_match = re.search(r'·\s*(\d+)', card_text)
        if card_number_match:
            meta_info['card_number'] = card_number_match.group(1)
    
    # Reference number - tìm trong phần "Reference number"
    reference_match = re.search(r'Reference\s+number[^<]*</td>\s*</tr>\s*<tr>\s*<td[^>]*>\s*<div[^>]*>([^<]+)', body_html, re.IGNORECASE | re.DOTALL)
    if reference_match:
        meta_info['reference_number'] = reference_match.group(1).strip()
    
    return meta_info


def is_meta_receipt_email(subject: str) -> bool:
    """
    Kiểm tra xem email có phải là Meta receipt không
    """
    return any(subject.startswith(pattern) for pattern in META_RECEIPT_SUBJECTS)


def build_email_filter(received_from: str = None, received_to: str = None) -> str:
    """
    Xây dựng filter string cho Microsoft Graph API
    """
    filters = []
    
    if received_from:
        filters.append(f"receivedDateTime ge {received_from}T00:00:00Z")
    if received_to:
        filters.append(f"receivedDateTime le {received_to}T23:59:59Z")
    
    return ' and '.join(filters) if filters else None


def get_email_api_params(top: int = 999, filter_str: str = None) -> Dict[str, Any]:
    """
    Tạo parameters cho Microsoft Graph API email request
    """
    params = {
        "$top": top,
        "$select": "id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,sentDateTime,isRead,hasAttachments,body,bodyPreview,importance,conversationId,conversationIndex,flag,categories,attachments",
    }
    
    if filter_str:
        params["$filter"] = filter_str
    
    return params 