"""
Test logic mới: chỉ lấy account_id và transaction_id từ body_preview
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.email_utils_bs4 import extract_meta_receipt_info_combined

def test_updated_logic():
    """Test logic mới với body_preview và body_html"""
    print("=== Test Logic Mới ===")
    
    # Body preview chỉ chứa account_id và transaction_id
    body_preview = """Biên lai của:
Meraki -TH-T255-884816463475062 (884816463475062)
ID giao dịch
24051431934546764-24122761920747095

Tóm tắt thông tin thanh toán
Số tiền đã lập hóa đơn
1,87 US$ (USD)
Phương thức thanh toán
Visa · 1582
Khoảng ngày
00:00 19 tháng 7, 2025 - 07:35 19 tháng 7"""
    
    # Body HTML chứa đầy đủ thông tin
    body_html = """
    <div class="mb_inl">$76.00 USD</div>
    <div class="mb_inl">Visa · 1582</div>
    <div class="mb_inl">REF123456789</div>
    <div class="mb_inl">Meraki -TH-T255-884816463475062 (884816463475062)</div>
    <div class="mb_inl">24051431934546764-24122761920747095</div>
    """
    
    print("📋 Body Preview:")
    print(body_preview)
    print("\n📋 Body HTML:")
    print(body_html)
    
    # Test với cả body_preview và body_html
    result = extract_meta_receipt_info_combined(body_html, body_preview)
    
    print("\n📋 Kết quả trích xuất:")
    print(f"Account ID: {result.get('account_id', 'Không tìm thấy')}")
    print(f"Transaction ID: {result.get('transaction_id', 'Không tìm thấy')}")
    print(f"Payment: {result.get('payment', 'Không tìm thấy')}")
    print(f"Card Type: {result.get('card_type', 'Không tìm thấy')}")
    print(f"Card Number: {result.get('card_number', 'Không tìm thấy')}")
    print(f"Card Text: {result.get('card_text', 'Không tìm thấy')}")
    print(f"Reference Number: {result.get('reference_number', 'Không tìm thấy')}")
    print(f"Date Range: {result.get('date_range', 'Không tìm thấy')}")
    
    # Kiểm tra kết quả mong đợi
    expected = {
        'account_id': '884816463475062',  # Từ body_preview
        'transaction_id': '24051431934546764-24122761920747095',  # Từ body_preview
        'payment': '76.00',  # Từ body_html
        'card_type': 'Visa',  # Từ body_html
        'card_number': '1582',  # Từ body_html
        'card_text': 'Visa · 1582',  # Từ body_html
        'reference_number': 'REF123456789'  # Từ body_html
    }
    
    print("\n✅ Kết quả mong đợi:")
    success_count = 0
    for key, value in expected.items():
        actual = result.get(key, 'Không tìm thấy')
        status = "✅" if actual == value else "❌"
        print(f"{status} {key}: {actual} (mong đợi: {value})")
        if actual == value:
            success_count += 1
    
    print(f"\n📊 Tỷ lệ thành công: {success_count}/{len(expected)} ({success_count/len(expected)*100:.1f}%)")
    
    # Test chỉ với body_html (không có body_preview)
    print("\n=== Test Chỉ Với Body HTML ===")
    result_html_only = extract_meta_receipt_info_combined(body_html, None)
    
    print("📋 Kết quả chỉ với body_html:")
    print(f"Account ID: {result_html_only.get('account_id', 'Không tìm thấy')}")
    print(f"Transaction ID: {result_html_only.get('transaction_id', 'Không tìm thấy')}")
    print(f"Payment: {result_html_only.get('payment', 'Không tìm thấy')}")
    print(f"Card Type: {result_html_only.get('card_type', 'Không tìm thấy')}")
    print(f"Card Number: {result_html_only.get('card_number', 'Không tìm thấy')}")
    
    return result

if __name__ == "__main__":
    print("🧪 Test Logic Mới")
    complete_result = test_updated_logic()
    print("\n�� Hoàn thành test!") 