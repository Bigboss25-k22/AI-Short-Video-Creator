# Video Script Generator API

API tự động tạo kịch bản video với hình ảnh và âm thanh sử dụng AI.

## Tính năng chính

- 🤖 Tự động tạo kịch bản video từ chủ đề
- 🎨 Tạo hình ảnh cho từng cảnh sử dụng Stable Diffusion
- 🔊 Tạo giọng nói từ text sử dụng Google TTS
- 🔍 Tìm kiếm và gợi ý nội dung từ YouTube và TikTok
- 👥 Quản lý người dùng và xác thực
- 📱 API RESTful đầy đủ với Swagger documentation

## Cấu trúc dự án

```
app/
├── api/                    # API endpoints
│   ├── video_script.py    # API xử lý kịch bản video
│   ├── voice.py          # API xử lý âm thanh
│   ├── image.py          # API xử lý hình ảnh
│   ├── auth.py           # API xác thực
│   └── user.py           # API quản lý người dùng
├── core/                  # Cấu hình cốt lõi
│   └── config.py         # Cấu hình ứng dụng
├── crud/                  # Database operations
│   └── video_script.py   # CRUD cho kịch bản video
├── models/               # Database models
│   ├── video_script.py   # Model kịch bản video
│   ├── user.py          # Model người dùng
│   └── token.py         # Model token
├── schemas/              # Pydantic schemas
│   ├── video_script.py   # Schema kịch bản video
│   ├── voice.py         # Schema âm thanh
│   └── image.py         # Schema hình ảnh
├── services/             # Business logic
│   ├── deepseek_service.py    # Service tạo kịch bản
│   ├── google_tts_service.py  # Service chuyển text thành giọng nói
│   └── image_generation_service.py # Service tạo hình ảnh
└── main.py               # Entry point
```

## Công nghệ sử dụng

### Core Framework
- FastAPI - Framework API hiện đại, nhanh
- SQLAlchemy - ORM cho database
- Alembic - Database migrations
- Pydantic - Data validation

### Database
- PostgreSQL - Database chính

### AI Services
- DeepSeek (OpenRouter) - Tạo kịch bản
- Google Text-to-Speech - Tạo giọng nói
- Replicate (Stable Diffusion) - Tạo hình ảnh

### Authentication & Security
- JWT - Xác thực người dùng
- Bcrypt - Mã hóa mật khẩu

### File Processing
- Pillow - Xử lý hình ảnh
- Pydub - Xử lý âm thanh

## Cài đặt và chạy

1. **Cài đặt dependencies**:
```bash
pip install -r requirements.txt
```

2. **Cấu hình môi trường**:
Tạo file `.env` trong thư mục `app` với các biến sau:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# AI Services
DEEPSEEK_API_KEY=your_deepseek_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
REPLICATE_API_TOKEN=your_replicate_api_token
REPLICATE_MODEL_ID=stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b
```

3. **Khởi tạo database**:
```bash
# Tạo database
createdb dbname

# Chạy migrations
alembic upgrade head
```

4. **Chạy server**:
```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/refresh` - Làm mới token
- `POST /api/auth/register` - Đăng ký

### Video Script
- `POST /api/video-scripts/generate` - Tạo kịch bản mới
- `GET /api/video-scripts/{script_id}` - Lấy thông tin kịch bản
- `PUT /api/video-scripts/{script_id}` - Cập nhật kịch bản
- `DELETE /api/video-scripts/{script_id}` - Xóa kịch bản

### Image Generation
- `POST /api/images/generate` - Tạo hình ảnh cho cảnh
- `POST /api/images/generate-for-script/{script_id}` - Tạo hình ảnh cho toàn bộ script
- `GET /api/images/list/{script_id}` - Lấy danh sách hình ảnh của script

### Voice Generation
- `POST /api/voice/text-to-speech` - Tạo giọng nói từ text
- `POST /api/voice/script-to-speech/{script_id}` - Tạo giọng nói cho toàn bộ script
- `GET /api/voice/play/{scene_id}` - Nghe thử giọng nói của scene
- `GET /api/voice/play-script/{script_id}` - Nghe thử giọng nói của toàn bộ script

## Ví dụ sử dụng

1. **Tạo kịch bản video**:
```bash
curl -X POST "http://localhost:8000/api/video-scripts/generate" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
           "topic": "Lần đầu bị mẹ mắng khi trở thành sinh viên",
           "target_audience": "Sinh viên",
           "duration": 90
         }'
```

2. **Tạo hình ảnh cho tất cả cảnh**:
```bash
curl -X POST "http://localhost:8000/api/images/generate-for-script/{script_id}" \
     -H "accept: application/json"
```

3. **Tạo âm thanh cho tất cả cảnh**:
```bash
curl -X POST "http://localhost:8000/api/voice/script-to-speech/{script_id}" \
     -H "accept: application/json" \
     -d '{
           "voice_id": "vi-VN-Standard-A",
           "speed": 1.0
         }'
```

4. **Nghe thử âm thanh**:
```bash
# Nghe thử một scene
curl -X GET "http://localhost:8000/api/voice/play/{scene_id}" --output voice.mp3

# Nghe thử toàn bộ script
curl -X GET "http://localhost:8000/api/voice/play-script/{script_id}" --output script.mp3
```

## Xử lý lỗi

API trả về các mã lỗi phù hợp:
- 400: Bad Request (thiếu thông tin)
- 401: Unauthorized (chưa xác thực)
- 404: Not Found (không tìm thấy tài nguyên)
- 500: Internal Server Error (lỗi server)

## Phát triển

1. **Tạo migration mới**:
```bash
alembic revision --autogenerate -m "description"
```

2. **Chạy tests**:
```bash
pytest
```

3. **Format code**:
```bash
black .
```

## Đóng góp

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Tạo Pull Request



