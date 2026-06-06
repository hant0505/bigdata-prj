# config.py
MINIO_ENDPOINT = "34.142.199.71:9000"   
MINIO_ACCESS_KEY = "admin"   
MINIO_SECRET_KEY = "12345678"  
BUCKET_NAME = "imdb"                   

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