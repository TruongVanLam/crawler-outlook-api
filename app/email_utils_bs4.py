"""
Email processing utilities using BeautifulSoup
"""
from typing import Dict, Any
from bs4 import BeautifulSoup
from .config import META_RECEIPT_SUBJECTS


def convert_vietnamese_date_to_english(date_text: str) -> str:
    """
    Convert ngày tháng tiếng Việt sang tiếng Anh
    """
    if not date_text:
        return date_text
    
    # Mapping tháng tiếng Việt sang tiếng Anh
    month_mapping = {
        'tháng 1': 'Jan', 'tháng 2': 'Feb', 'tháng 3': 'Mar', 'tháng 4': 'Apr',
        'tháng 5': 'May', 'tháng 6': 'Jun', 'tháng 7': 'Jul', 'tháng 8': 'Aug',
        'tháng 9': 'Sep', 'tháng 10': 'Oct', 'tháng 11': 'Nov', 'tháng 12': 'Dec'
    }
    
    converted_text = date_text
    
    # Thay thế tất cả các tháng tiếng Việt
    for vi_month, en_month in month_mapping.items():
        converted_text = converted_text.replace(vi_month, en_month)
    
    return converted_text.strip()


def extract_card_info(card_text: str) -> Dict[str, str]:
    """
    Trích xuất thông tin thẻ từ text
    Trả về cả loại thẻ và số thẻ
    """
    import re
    
    card_info = {}
    
    # Tìm loại thẻ (Visa, Mastercard, etc.)
    card_type_match = re.search(r'(Visa|Mastercard|American Express|Amex|Discover)', card_text, re.IGNORECASE)
    if card_type_match:
        card_info['card_type'] = card_type_match.group(1)
    
    # Tìm số thẻ (sau dấu ·)
    card_number_match = re.search(r'·\s*(\d+)', card_text)
    if card_number_match:
        card_info['card_number'] = card_number_match.group(1)
    
    # Giữ nguyên text gốc
    card_info['card_text'] = card_text.strip()
    
    return card_info


def extract_meta_receipt_info_bs4(body_html: str) -> Dict[str, Any]:
    """
    Trích xuất thông tin từ body HTML của email Meta receipt sử dụng BeautifulSoup.
    """
    meta_info = {}
    
    # Parse HTML
    soup = BeautifulSoup(body_html, 'html.parser')
    
    # Account ID - tìm trong phần "Transaction for"
    transaction_for_divs = soup.find_all('div', string=lambda text: text and 'Transaction for' in text)
    if transaction_for_divs:
        # Tìm div chứa account info (thường là div kế tiếp)
        for div in transaction_for_divs:
            parent = div.parent
            if parent:
                # Tìm div chứa account text
                account_div = parent.find_next_sibling('div') or parent.find('div')
                if account_div:
                    account_text = account_div.get_text(strip=True)
                    # Trích xuất số account ID từ text "Meraki-Linh-T2219-1255380388827210 (1255380388827210)"
                    import re
                    account_id_match = re.search(r'\((\d{10,})\)', account_text)
                    if account_id_match:
                        meta_info['account_id'] = account_id_match.group(1)
                        break
    
    # Transaction ID - tìm trong phần "Transaction ID"
    transaction_id_divs = soup.find_all('div', string=lambda text: text and 'Transaction ID' in text)
    if transaction_id_divs:
        for div in transaction_id_divs:
            parent = div.parent
            if parent:
                # Tìm link chứa transaction ID
                link = parent.find('a')
                if link:
                    meta_info['transaction_id'] = link.get_text(strip=True)
                    break
    
    # Payment amount - tìm trong phần "Amount billed"
    amount_divs = soup.find_all('div', string=lambda text: text and 'Amount billed' in text)
    if amount_divs:
        for div in amount_divs:
            # Tìm div chứa số tiền (thường là div kế tiếp)
            parent = div.parent
            if parent:
                amount_div = parent.find_next_sibling('div') or parent.find('div', class_='mb_inl')
                if amount_div:
                    amount_text = amount_div.get_text(strip=True)
                    # Trích xuất số từ "$7.00 USD"
                    import re
                    amount_match = re.search(r'\$([\d,]+\.?\d*)', amount_text)
                    if amount_match:
                        meta_info['payment'] = amount_match.group(1).replace(',', '')
                        break
    
    # Card number - tìm trong phần "PAYMENT METHOD"
    payment_method_divs = soup.find_all('div', string=lambda text: text and 'PAYMENT METHOD' in text)
    if payment_method_divs:
        for div in payment_method_divs:
            parent = div.parent
            if parent:
                # Tìm div chứa thông tin thẻ
                card_div = parent.find_next_sibling('div') or parent.find('div', class_='mb_inl')
                if card_div:
                    card_text = card_div.get_text(strip=True)
                    # Trích xuất số thẻ từ "Visa · 1582"
                    import re
                    card_number_match = re.search(r'·\s*(\d+)', card_text)
                    if card_number_match:
                        meta_info['card_number'] = card_number_match.group(1)
                        break
    
    # Reference number - tìm trong phần "Reference number"
    reference_divs = soup.find_all('div', string=lambda text: text and 'Reference number' in text)
    if reference_divs:
        for div in reference_divs:
            parent = div.parent
            if parent:
                # Tìm div chứa reference number
                ref_div = parent.find_next_sibling('div') or parent.find('div', class_='mb_inl')
                if ref_div:
                    meta_info['reference_number'] = ref_div.get_text(strip=True)
                    break
    
    return meta_info


def extract_meta_receipt_info_by_text_search(body_html: str) -> Dict[str, Any]:
    """
    Trích xuất thông tin bằng cách tìm kiếm text cụ thể trong HTML.
    """
    meta_info = {}
    soup = BeautifulSoup(body_html, 'html.parser')
    
    # Tìm tất cả text nodes
    text_nodes = soup.find_all(text=True)
    
    for i, text in enumerate(text_nodes):
        text = text.strip()
        
        # Account ID
        if 'Transaction for' in text and i + 1 < len(text_nodes):
            next_text = text_nodes[i + 1].strip()
            import re
            account_id_match = re.search(r'\((\d{10,})\)', next_text)
            if account_id_match:
                meta_info['account_id'] = account_id_match.group(1)
        
        # Transaction ID
        elif 'Transaction ID' in text and i + 1 < len(text_nodes):
            next_text = text_nodes[i + 1].strip()
            if next_text and len(next_text) > 10:  # Transaction ID thường dài
                meta_info['transaction_id'] = next_text
        
        # Payment amount
        elif 'Amount billed' in text and i + 1 < len(text_nodes):
            next_text = text_nodes[i + 1].strip()
            import re
            amount_match = re.search(r'\$([\d,]+\.?\d*)', next_text)
            if amount_match:
                meta_info['payment'] = amount_match.group(1).replace(',', '')
        
        # Card number
        elif 'PAYMENT METHOD' in text and i + 1 < len(text_nodes):
            next_text = text_nodes[i + 1].strip()
            # Trích xuất thông tin thẻ đầy đủ
            card_info = extract_card_info(next_text)
            if card_info:
                meta_info.update(card_info)
        
        # Reference number
        elif 'Reference number' in text and i + 1 < len(text_nodes):
            next_text = text_nodes[i + 1].strip()
            if next_text and len(next_text) > 5:  # Reference number thường có độ dài nhất định
                meta_info['reference_number'] = next_text
    
    return meta_info


def extract_meta_receipt_info_by_css_selectors(body_html: str) -> Dict[str, Any]:
    """
    Trích xuất thông tin bằng CSS selectors.
    """
    meta_info = {}
    soup = BeautifulSoup(body_html, 'html.parser')
    
    # Tìm tất cả text nodes để tìm payment
    all_text = soup.get_text()
    
    # Tìm payment amount - nhiều pattern khác nhau
    import re
    payment_patterns = [
        r'\$([\d,]+\.?\d*)\s*USD',  # $76.00 USD
        r'([\d,]+\.?\d*)\s*US\$',   # 1,87 US$
        r'([\d,]+\.?\d*)\s*USD',    # 1,87 USD
        r'\$([\d,]+\.?\d*)',        # $76.00
    ]
    
    for pattern in payment_patterns:
        amount_match = re.search(pattern, all_text)
        if amount_match:
            meta_info['payment'] = amount_match.group(1).replace(',', '')
            break
    
    # Tìm các div có class 'mb_inl' (thường chứa thông tin chính)
    mb_inl_divs = soup.find_all('div', class_='mb_inl')
    
    for div in mb_inl_divs:
        text = div.get_text(strip=True)
        
        # Card number
        if '·' in text and any(char.isdigit() for char in text):
            card_info = extract_card_info(text)
            if card_info:
                meta_info.update(card_info)
        
        # Account ID
        elif len(text) > 20 and '(' in text and ')' in text:
            account_id_match = re.search(r'\((\d{10,})\)', text)
            if account_id_match:
                meta_info['account_id'] = account_id_match.group(1)
        
        # Transaction ID - tránh lấy nhầm ngày tháng
        elif len(text) > 30 and '-' in text:
            # Kiểm tra để tránh lấy nhầm ngày tháng
            # Pattern cho ngày tháng tiếng Việt
            vi_date_pattern = r'\d{1,2}:\d{2}\s+\d{1,2}\s+tháng\s+\d{1,2}'
            # Pattern cho ngày tháng tiếng Anh
            en_date_pattern = r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
            if (not re.search(vi_date_pattern, text) and 
                not re.search(en_date_pattern, text)):
                meta_info['transaction_id'] = text
        
        # Reference number
        elif len(text) == 10 and text.isalnum():
            meta_info['reference_number'] = text
    
    return meta_info


def extract_meta_receipt_info_from_preview(body_preview: str) -> Dict[str, Any]:
    """
    Trích xuất thông tin từ body_preview (text đơn giản).
    Xử lý cả 4 case:
    - Case 1: "This is not an invoice" + "Transaction for" (EN)
    - Case 2: "Receipt for" (EN)
    - Case 3: "Biên lai của" (VI)
    - Case 4: "Giao dịch của" (VI)
    """
    meta_info = {}
    
    if not body_preview:
        return meta_info
    
    # Chia text thành các dòng
    lines = [line.strip() for line in body_preview.split('\n') if line.strip()]
    
    for i, line in enumerate(lines):
        # Account ID - tìm trong cả 4 case
        if any(keyword in line for keyword in ['Transaction for', 'Receipt for', 'Biên lai của', 'Giao dịch của']):
            # Tìm dòng tiếp theo chứa account info
            if i + 1 < len(lines):
                account_line = lines[i + 1]
                import re
                account_id_match = re.search(r'\((\d{10,})\)', account_line)
                if account_id_match:
                    meta_info['account_id'] = account_id_match.group(1)
        
        # Transaction ID - cả tiếng Anh và tiếng Việt
        elif any(keyword in line for keyword in ['Transaction ID', 'ID giao dịch']):
            # Tìm dòng tiếp theo chứa transaction ID
            if i + 1 < len(lines):
                transaction_id = lines[i + 1].strip()
                # Kiểm tra để tránh lấy nhầm ngày tháng
                import re
                # Pattern cho ngày tháng tiếng Việt
                vi_date_pattern = r'\d{1,2}:\d{2}\s+\d{1,2}\s+tháng\s+\d{1,2}'
                # Pattern cho ngày tháng tiếng Anh
                en_date_pattern = r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
                # Nếu có pattern ngày tháng thì bỏ qua
                if (not re.search(vi_date_pattern, transaction_id) and 
                    not re.search(en_date_pattern, transaction_id) and 
                    transaction_id and '-' in transaction_id):
                    meta_info['transaction_id'] = transaction_id
        

    
    return meta_info


def extract_meta_receipt_info_combined(body_html: str = None, body_preview: str = None) -> Dict[str, Any]:
    """
    Trích xuất thông tin kết hợp từ cả body_html và body_preview.
    - body_preview: chỉ lấy account_id và transaction_id
    - body_html: lấy payment, card_number, reference_number và các thông tin khác
    """
    meta_info = {}
    
    # Thử trích xuất từ body_preview trước (chỉ account_id và transaction_id)
    if body_preview:
        preview_info = extract_meta_receipt_info_from_preview(body_preview)
        meta_info.update(preview_info)
    
    # Luôn lấy thông tin từ body_html cho payment, card_number, reference_number
    if body_html:
        html_info = extract_meta_receipt_info_by_css_selectors(body_html)
        # Cập nhật tất cả thông tin từ body_html
        meta_info.update(html_info)
    
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