# Claude AI Chat

## Setup

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
```

Sửa `.env`, thêm API key của bạn:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Chạy server:
```bash
uvicorn main:app --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

Mở http://localhost:5173

## Lấy API Key
Đăng ký tại https://console.anthropic.com → API Keys → Create Key
