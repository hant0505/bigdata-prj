# etl_bronze.py
from pyspark.sql import SparkSession
from config import *

def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("IMDb ETL - Bronze Layer")
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}")
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark

def load_bronze(spark, table_name, local_path):
    print(f"[BRONZE] Loading: {table_name}")
    df = spark.read.parquet(local_path)
    print(f"  → Rows: {df.count():,} | Cols: {df.columns}")
    df.write.mode("overwrite").parquet(f"{BRONZE_PATH}/{table_name}")
    print(f"  ✓ Done: {BRONZE_PATH}/{table_name}\n")

if __name__ == "__main__":
    spark = create_spark_session()

    table_paths = {
        "movies":           "/data/movies.parquet",
        "actors":           "/data/actors.parquet",
        "directors":        "/data/directors.parquet",
        "roles":            "/data/roles.parquet",
        "movies_genres":    "/data/movies_genres.parquet",
        "movies_directors": "/data/movies_directors.parquet",
        "directors_genres": "/data/directors_genres.parquet",
    }

    for table, path in table_paths.items():
        load_bronze(spark, table, path)

    print("=== BRONZE LAYER COMPLETE ===")
    spark.stop()