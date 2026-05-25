# SQL Intelligence — Hướng dẫn chạy

## Cấu trúc project

```
agent/
├── agents/
│   └── agents.py          # 4 agents: Planner, Generator, Executor, Interpreter
├── tools/
│   └── schema_tool.py     # Tools: GetSchema, ExecuteSQL
├── data/
│   └── *.parquet          # Silver parquet files synced from MinIO
├── main.py                # Pipeline chính + CLI
├── requirements.txt
└── .env                   # API keys (tự tạo)
```

---

## Bước 1 — Cài đặt

```bash
# Tạo virtual environment (khuyến nghị)
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows

# Cài dependencies
pip install -r requirements.txt
```

---

## Bước 2 — Cấu hình API Key

Tạo file `.env` trong folder agent

```bash
# Dùng Gemini (theo SDS của nhóm)
GOOGLE_API_KEY=your_gemini_api_key_here
```

Lấy Gemini API key miễn phí tại: https://aistudio.google.com/apikey

Load .env trước khi chạy:

```bash
export $(cat .env | xargs)
# hoặc thêm vào đầu main.py: from dotenv import load_dotenv; load_dotenv()
```

## pip install "crewai[google-genai]"

## Bước 3 — Chạy CLI (đơn giản nhất)

```bash
cd agent

# Chạy với câu hỏi mặc định
python main.py

# Chạy với câu hỏi tùy chỉnh
python main.py "Top 5 nghệ sĩ có doanh thu cao nhất?"
python main.py "Thể loại nhạc nào có nhiều bài hát nhất?"
python main.py "Khách hàng từ Brazil chi tiêu bao nhiêu?"
```

---

## Bước 4 — Chạy UI Streamlit

```bash
cd agent
streamlit run ui/app.py
```

Trình duyệt tự mở tại: http://localhost:8501

---

## Luồng hoạt động

```
User question
     │
     ▼
Agent 1: Schema-Aware Query Planner
  - Đọc schema của silver parquet files
  - Xác định bảng, cột, JOIN path cần dùng
  - Tạo kế hoạch truy vấn
     │
     ▼
Agent 2: SQL Generator
  - Nhận kế hoạch từ Agent 1
  - Viết SQL SELECT hoàn chỉnh
     │
     ▼
Agent 3: SQL Executor & QA
  - Chạy SQL trên silver parquet dataset
  - Nếu lỗi: báo lại Agent 2 sửa (max 3 lần)
  - Nếu OK: trả kết quả
     │
     ▼
Agent 4: Data Interpreter
  - Đọc kết quả số liệu
  - Dịch thành câu trả lời tiếng Việt dễ hiểu
     │
     ▼
User gets answer ✅
```

---

## Nâng cấp lên Big Data (PySpark + MinIO)

Để mở rộng theo đúng SDS (Big Data version):

1. **Thay SQLite bằng Spark SQL:**
   - Cài: `pip install pyspark`
   - Đổi `ExecuteSQLTool` để chạy `spark.sql(query)` thay vì `sqlite3`

2. **Thêm MinIO storage:**
   - Cài MinIO local: `docker run -p 9000:9000 minio/minio server /data`
   - Load data Parquet từ MinIO vào Spark DataFrame

3. **Medallion Architecture:**
   - Bronze layer: Raw source data (CSV/JSON hoặc nguồn nhập vào)
   - Silver layer: Cleaned Parquet trên MinIO
   - Gold layer: Aggregated tables cho analytics

---

## Troubleshooting

| Lỗi                           | Cách xử lý                                          |
| ----------------------------- | --------------------------------------------------- |
| `No API key`                  | Set biến môi trường GOOGLE_API_KEY                  |
| `ModuleNotFoundError: crewai` | Chạy `pip install crewai`                           |
| `No parquet files found`       | Kiểm tra xem đã sync dữ liệu silver từ MinIO chưa |
| SQL error từ Agent            | Agent sẽ tự retry, nếu vẫn lỗi thì thử câu hỏi khác |
