# Mail API - Microsoft Graph Integration với PostgreSQL

API để đọc email từ Microsoft Outlook sử dụng Microsoft Graph API và lưu trữ vào PostgreSQL database.

## Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình database PostgreSQL

Tạo file `.env` với nội dung:
```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/mail_api_db

# Microsoft Graph API Configuration
CLIENT_ID=b6239e39-c5f9-4704-ac0d-bcb0e0dc87b6
CLIENT_SECRET=cOb8Q~KsEr2B.UpGCBxp5Sqcs6JnBs~Osc_~fa4B
REDIRECT_URI=http://localhost:8000/callback

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 3. Tạo database PostgreSQL
```sql
CREATE DATABASE mail_api_db;
```

### 4. Khởi tạo database
```bash
# Chạy server
python main.py

# Trong terminal khác, gọi API để khởi tạo database
curl -X POST http://localhost:8000/init-db
```

### 5. Chạy server
```bash
python main.py
```

Server sẽ chạy tại `http://localhost:8000`

## Cấu trúc Database

### Bảng `accounts`
- Lưu thông tin tài khoản người dùng
- Fields: id, email, name, user_principal_name, display_name, created_at, updated_at, is_active

### Bảng `auth_tokens`
- Lưu thông tin token xác thực
- Fields: id, account_id, access_token, refresh_token, expires_at, scope, created_at, updated_at, is_active

### Bảng `emails`
- Lưu thông tin email
- Fields: id, account_id, message_id, subject, from_email, to_recipients, body, received_date_time, is_read, has_attachments, etc.

### Bảng `email_attachments`
- Lưu thông tin file đính kèm
- Fields: id, email_id, attachment_id, name, content_type, size, content_bytes, file_path

## Cách sử dụng

### 1. Xác thực tài khoản mới

#### Bước 1: Lấy URL đăng nhập
```bash
GET /login
```

Response:
```json
{
  "login_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?...",
  "message": "Truy cập URL này để đăng nhập Microsoft"
}
```

#### Bước 2: Đăng nhập Microsoft
Truy cập URL từ response trên để đăng nhập Microsoft.

#### Bước 3: Nhận callback
Sau khi đăng nhập thành công, Microsoft sẽ redirect về:
```
GET /auth/callback?code=AUTH_CODE_HERE
```

Response:
```json
{
  "message": "Thêm tài khoản thành công!",
  "email": "user@example.com",
  "account_id": 1
}
```

### 2. Khởi tạo database
```bash
POST /init-db
```

### 3. Lấy danh sách accounts
```bash
GET /accounts
```

### 4. Kiểm tra trạng thái xác thực
```bash
GET /status/{account_id}
```

### 5. Đồng bộ email từ Microsoft Graph
```bash
GET /mails/sync?account_id={account_id}&top=50
```

### 6. Lấy danh sách email
```bash
GET /mails?account_id={account_id}&top=10&skip=0&is_read=false&has_attachments=true
```

**Parameters:**
- `account_id`: ID của tài khoản (bắt buộc)
- `top`: Số lượng email tối đa (mặc định: 10)
- `skip`: Số email bỏ qua cho phân trang (mặc định: 0)
- `is_read`: Lọc theo trạng thái đọc (true/false)
- `has_attachments`: Lọc theo có file đính kèm (true/false)

### 7. Lấy email chưa đọc
```bash
GET /mails/unread?account_id={account_id}&top=10&skip=0
```

### 8. Tìm kiếm email
```bash
GET /mails/search?account_id={account_id}&query=keyword&top=10&skip=0
```

### 9. Lấy chi tiết email
```bash
GET /mails/{message_id}?account_id={account_id}
```

## Ví dụ sử dụng

### Đăng nhập tài khoản mới
```bash
# Bước 1: Lấy URL đăng nhập
curl "http://localhost:8000/login"

# Bước 2: Truy cập URL từ response để đăng nhập Microsoft
# Bước 3: Microsoft sẽ redirect về /auth/callback với code
```

### Lấy danh sách accounts
```bash
curl "http://localhost:8000/accounts"
```

### Đồng bộ email cho account ID 1
```bash
curl "http://localhost:8000/mails/sync?account_id=1&top=50"
```

### Lấy 10 email mới nhất của account ID 1
```bash
curl "http://localhost:8000/mails?account_id=1&top=10"
```

### Lấy email chưa đọc của account ID 1
```bash
curl "http://localhost:8000/mails/unread?account_id=1&top=20"
```

### Tìm kiếm email có từ "meeting" trong account ID 1
```bash
curl "http://localhost:8000/mails/search?account_id=1&query=meeting"
```

### Lấy chi tiết email cụ thể
```bash
curl "http://localhost:8000/mails/AAMkAGVmMDEzMTM4LTZmYWUtNDdkNC1hMDZkLWRmM2NkM2M3ZjQ5OABGAAAAAAAiQ8W967B7TKBjgx9rVEURBwAiIsqMbYjsT5G-TvKJjecHAAAAAAEMAAAiIsqMbYjsT5G-TvKJjecHAAAYjqQeAAA=?account_id=1"
```

### Kiểm tra trạng thái xác thực của account ID 1
```bash
curl "http://localhost:8000/status/1"
```

## Tính năng

- ✅ Xác thực OAuth2 với Microsoft Graph API
- ✅ Lưu trữ token vào PostgreSQL database
- ✅ Tự động refresh token khi hết hạn
- ✅ Đồng bộ email từ Microsoft Graph vào database
- ✅ Đọc danh sách email với phân trang và filter
- ✅ Tìm kiếm email theo từ khóa
- ✅ Lấy chi tiết email
- ✅ Quản lý nhiều tài khoản
- ✅ Lưu trữ file đính kèm

## Lưu ý

- Cần có quyền `Mail.Read` để đọc email
- Cần có quyền `offline_access` để lấy refresh token
- Token được lưu trong database và tự động refresh khi hết hạn
- Email được lưu trong database để truy vấn nhanh hơn
- Cần đồng bộ email trước khi có thể đọc từ database 