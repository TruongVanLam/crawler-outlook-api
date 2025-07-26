# User Management System

Hệ thống quản lý user và phân quyền cho Mail API.

## Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy migration
```bash
python migration_add_users.py
```

## Cấu trúc Database

### Bảng `users`
- `id`: Primary key
- `email`: Email đăng nhập (unique)
- `password_hash`: Mật khẩu đã hash
- `role`: Vai trò (user, admin, ...)
- `created_at`: Thời gian tạo
- `updated_at`: Thời gian cập nhật

### Bảng `accounts` (đã cập nhật)
- Thêm trường `user_id`: Foreign key đến bảng users
- Mỗi account thuộc về một user

## API Endpoints

### User Authentication

#### 1. Đăng ký user mới
```http
POST /api/v1/users/register
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123",
    "role": "user"
}
```

#### 2. Đăng nhập
```http
POST /api/v1/users/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}
```

Response:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "user_id": 1,
    "email": "user@example.com",
    "role": "user"
}
```

#### 3. Lấy thông tin user hiện tại
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

### Account Management (theo User)

#### 1. Lấy danh sách accounts của user
```http
GET /api/v1/users/accounts?skip=0&limit=100
Authorization: Bearer <access_token>
```

#### 2. Tạo account mới
```http
POST /api/v1/users/accounts
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "email": "account@example.com",
    "name": "Account Name"
}
```

#### 3. Lấy thông tin chi tiết account
```http
GET /api/v1/users/accounts/{account_id}
Authorization: Bearer <access_token>
```

#### 4. Cập nhật account
```http
PUT /api/v1/users/accounts/{account_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "email": "newemail@example.com",
    "name": "New Name"
}
```

#### 5. Xóa account
```http
DELETE /api/v1/users/accounts/{account_id}
Authorization: Bearer <access_token>
```

### Email và Export (đã cập nhật)

#### 1. Lấy emails (yêu cầu xác thực)
```http
GET /api/v1/mails?account_ids=1,2&from_date=2024-01-01&to_date=2024-01-31
Authorization: Bearer <access_token>
```

#### 2. Export Meta receipts (yêu cầu xác thực)
```http
GET /api/v1/export/meta-receipts/?account_ids=1,2&from_date=2024-01-01&to_date=2024-01-31
Authorization: Bearer <access_token>
```

## Tính năng bảo mật

### 1. Xác thực JWT
- Tất cả endpoints quan trọng yêu cầu Bearer token
- Token có thời hạn 30 phút
- Tự động refresh khi cần

### 2. Phân quyền
- User chỉ có thể truy cập accounts của mình
- Kiểm tra quyền trước khi thực hiện các thao tác
- Trả về lỗi 403 nếu không có quyền

### 3. Password Security
- Sử dụng bcrypt để hash password
- Không lưu trữ password dạng plain text

## Ví dụ sử dụng

### 1. Tạo user và đăng nhập
```bash
# Đăng ký
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123", "role": "admin"}'

# Đăng nhập
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

### 2. Quản lý accounts
```bash
# Lấy danh sách accounts
curl -X GET "http://localhost:8000/api/v1/users/accounts" \
  -H "Authorization: Bearer <your_token>"

# Tạo account mới
curl -X POST "http://localhost:8000/api/v1/users/accounts" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test Account"}'
```

### 3. Lấy emails và export
```bash
# Lấy emails
curl -X GET "http://localhost:8000/api/v1/mails?account_ids=1&from_date=2024-01-01&to_date=2024-01-31" \
  -H "Authorization: Bearer <your_token>"

# Export Meta receipts
curl -X GET "http://localhost:8000/api/v1/export/meta-receipts/?account_ids=1&from_date=2024-01-01&to_date=2024-01-31" \
  -H "Authorization: Bearer <your_token>" \
  --output meta_receipts.zip
```

## Lưu ý quan trọng

1. **Thay đổi SECRET_KEY**: Trong file `app/user_auth.py`, thay đổi `SECRET_KEY` thành một giá trị bảo mật trong production.

2. **Migration**: Chạy migration trước khi sử dụng hệ thống.

3. **Backup**: Backup database trước khi chạy migration.

4. **HTTPS**: Sử dụng HTTPS trong production để bảo mật token.

5. **Rate Limiting**: Cân nhắc thêm rate limiting cho các endpoint authentication. 