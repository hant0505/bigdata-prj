# config.py
MINIO_ENDPOINT = "34.142.199.71:9000"   # ← đổi thành IP:9000 (S3 API port, không phải 9001)
MINIO_ACCESS_KEY = "admin"   # ← tài khoản được cấp
MINIO_SECRET_KEY = "12345678"   # ← mật khẩu được cấp
BUCKET_NAME = "imdb"                     # ← tên bucket đã có sẵn trên server

BRONZE_PATH = f"s3a://{BUCKET_NAME}/bronze"
SILVER_PATH = f"s3a://{BUCKET_NAME}/silver"

TABLES = [
    "movies",
    "actors",
    "directors",
    "roles",
    "movies_genres",
    "movies_directors",
    "directors_genres",
]