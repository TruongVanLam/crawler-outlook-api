# Auto Sync Service

## Tổng quan

Auto Sync Service là một tính năng tự động đồng bộ email khi có account mới được tạo. Service này chạy trong background và sẽ:

1. **Tự động đồng bộ email cho account mới**: Khi có account mới được tạo thông qua OAuth flow, account sẽ được thêm vào queue và tự động đồng bộ email trong 1 tháng gần nhất.

2. **Đồng bộ email hàng ngày**: Service sẽ chạy 1 lần mỗi ngày vào lúc bước sang ngày mới để đồng bộ email mới cho tất cả các account đang hoạt động (tối đa 999 emails).

3. **Xử lý Meta receipts**: Sau khi đồng bộ email, service sẽ tự động xử lý và tạo Meta receipts.

## Cách hoạt động

### 1. Khởi động tự động
- Service sẽ tự động khởi động khi ứng dụng FastAPI khởi động
- Service chạy trong background thread và không ảnh hưởng đến performance của API

### 2. Xử lý account mới
- Khi user hoàn thành OAuth flow tại `/auth/callback`, account mới sẽ được tạo
- Account ID sẽ được tự động thêm vào sync queue
- Service sẽ xử lý account này trong lần chạy tiếp theo

### 3. Đồng bộ định kỳ
- Service chạy mỗi 1 phút để kiểm tra ngày mới
- Kiểm tra tất cả account đang hoạt động có token hợp lệ
- Thực hiện đồng bộ email mới hàng ngày (chỉ 1 lần/ngày)
- Tối đa 999 emails được đồng bộ cho mỗi account
- Xử lý Meta receipts cho email mới

## API Endpoints

### 1. Khởi động Auto Sync Service
```http
POST /api/v1/auto-sync/start
```

**Response:**
```json
{
  "message": "Auto sync service started successfully",
  "status": {
    "is_running": true,
    "sync_interval": 300,
    "new_accounts_count": 0,
    "new_accounts": []
  }
}
```

### 2. Dừng Auto Sync Service
```http
POST /api/v1/auto-sync/stop
```

**Response:**
```json
{
  "message": "Auto sync service stopped successfully",
  "status": {
    "is_running": false,
    "sync_interval": 300,
    "new_accounts_count": 0,
    "new_accounts": []
  }
}
```

### 3. Kiểm tra trạng thái
```http
GET /api/v1/auto-sync/status
```

**Response:**
```json
{
  "status": {
    "is_running": true,
    "sync_interval": 300,
    "new_accounts_count": 1,
    "new_accounts": [1]
  }
}
```

### 4. Thêm account vào sync queue (thủ công)
```http
POST /api/v1/auto-sync/add-account/{account_id}
```

**Response:**
```json
{
  "message": "Account 1 added to auto sync queue",
  "status": {
    "is_running": true,
    "sync_interval": 300,
    "new_accounts_count": 1,
    "new_accounts": [1]
  }
}
```

## Cấu hình

### Sync Interval
Mặc định service chạy mỗi 1 phút (60 giây) để kiểm tra ngày mới. Có thể thay đổi trong `app/auto_sync_service.py`:

```python
self.sync_interval = 60  # 1 minute - check for new day
```

### Logging
Service sẽ log các hoạt động:
- Khi account được thêm vào queue
- Khi bắt đầu xử lý account
- Kết quả đồng bộ email
- Kết quả xử lý Meta receipts
- Lỗi nếu có

## Monitoring

### 1. Kiểm tra trạng thái service
```bash
curl -X GET http://localhost:8000/api/v1/auto-sync/status
```

### 2. Xem logs
Service sẽ in logs ra console:
```
Auto sync service started on startup
Added account 1 to auto sync queue
Processing initial sync for account 1
Initial sync completed for account 1: 15 emails synced
Meta receipts processed for account 1: 8 receipts
🔄 Starting daily sync for date: 2024-01-15
📊 Processing daily sync for 3 active accounts
📧 Processing daily sync for account 1 (user@example.com)
✅ Daily sync completed for account 1: 5 new emails
📄 Meta receipts processed for account 1: 3 receipts
📈 Daily sync summary: 3/3 accounts processed
📧 Total emails synced: 12
📄 Total receipts processed: 8
✅ Daily sync completed for date: 2024-01-15
```

### 3. Kiểm tra database
- Kiểm tra bảng `emails` để xem email đã được đồng bộ
- Kiểm tra bảng `meta_receipts` để xem Meta receipts đã được xử lý

## Troubleshooting

### 1. Service không khởi động
- Kiểm tra logs khi khởi động ứng dụng
- Đảm bảo database connection hoạt động
- Kiểm tra quyền truy cập database

### 2. Account không được xử lý
- Kiểm tra account có tồn tại và active không
- Kiểm tra account có valid auth token không
- Kiểm tra token có hết hạn không

### 3. Email không được đồng bộ
- Kiểm tra Graph API permissions
- Kiểm tra access token có quyền đọc email không
- Kiểm tra network connection

### 4. Meta receipts không được xử lý
- Kiểm tra email có phải Meta receipt không
- Kiểm tra email parsing logic
- Kiểm tra database constraints

## Testing

### 1. Test endpoints
```bash
python test_auto_sync.py
```

### 2. Test account creation
1. Khởi động API server
2. Hoàn thành OAuth flow cho account mới
3. Kiểm tra auto sync status
4. Monitor logs để xem quá trình sync

### 3. Test manual sync
```bash
# Thêm account vào queue
curl -X POST http://localhost:8000/api/v1/auto-sync/add-account/1

# Kiểm tra status
curl -X GET http://localhost:8000/api/v1/auto-sync/status
```

## Security Considerations

1. **Database Access**: Service sử dụng database connection pool để tránh connection leak
2. **Error Handling**: Tất cả exceptions được catch và log để tránh crash service
3. **Resource Management**: Service tự động đóng database connections
4. **Thread Safety**: Service sử dụng thread-safe operations

## Performance Considerations

1. **Background Processing**: Service chạy trong background thread không ảnh hưởng API performance
2. **Batch Processing**: Xử lý từng account một cách tuần tự để tránh overload
3. **Error Recovery**: Service tiếp tục chạy ngay cả khi có lỗi với một account
4. **Resource Cleanup**: Tự động cleanup resources sau mỗi lần xử lý 