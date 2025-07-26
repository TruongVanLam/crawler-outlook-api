# App Module Structure

Cấu trúc thư mục `app/` đã được tách ra từ `main.py` để code dễ quản lý hơn:

## Cấu trúc thư mục:

```
app/
├── __init__.py          # Python package
├── config.py            # Cấu hình và hằng số
├── auth.py              # Xác thực và quản lý token
├── email_utils.py       # Tiện ích xử lý email
├── graph_api.py         # Gọi Microsoft Graph API
├── services.py          # Business logic
├── routes.py            # API endpoints
└── README.md            # File này
```

## Mô tả từng module:

### `config.py`
- Chứa các cấu hình Microsoft Graph API
- Hằng số cho email filter patterns
- Giới hạn API

### `auth.py`
- Quản lý access token và refresh token
- Xác thực với Microsoft Graph API

### `email_utils.py`
- Trích xuất thông tin từ email Meta receipt
- Kiểm tra loại email
- Tạo filter cho API calls

### `graph_api.py`
- Các hàm gọi Microsoft Graph API
- Lấy emails, user info, attachments

### `services.py`
- Business logic cho việc đồng bộ email
- Class `EmailSyncService` xử lý logic chính

### `routes.py`
- Tất cả API endpoints
- Sử dụng services để xử lý logic

### `export_service.py`
- Service xuất Excel và tạo file ZIP
- Xử lý export Meta receipts theo yêu cầu

## Cách sử dụng:

1. Chạy `main_new.py` thay vì `main.py`
2. Tất cả endpoints giữ nguyên URL, chỉ thêm prefix `/api/v1`
3. Ví dụ: `/mails/sync-daily/` → `/api/v1/mails/sync-daily/`

## Endpoint mới - Export Meta Receipts:

```
GET /api/v1/export/meta-receipts/
```

**Parameters:**
- `account_ids`: Danh sách account IDs (comma-separated), ví dụ: "1,2,3"
- `from_date`: Ngày bắt đầu (YYYY-MM-DD), ví dụ: "2024-01-01"
- `to_date`: Ngày kết thúc (YYYY-MM-DD), ví dụ: "2024-01-31"

**Response:**
- File ZIP chứa các file Excel riêng cho từng account
- Mỗi file Excel có format: `['Date', 'account_id', 'transaction_id', 'payment', 'card_number', 'reference_number', 'status']`

**Ví dụ:**
```
GET /api/v1/export/meta-receipts/?account_ids=1,2&from_date=2024-01-01&to_date=2024-01-31
```

## Lợi ích:

- **Dễ bảo trì**: Mỗi module có trách nhiệm riêng
- **Dễ test**: Có thể test từng module riêng
- **Dễ mở rộng**: Thêm tính năng mới dễ dàng
- **Code sạch**: Logic được tách biệt rõ ràng 