from pyspark.sql import SparkSession
from config import *


def create_spark_session():
    return (
        SparkSession.builder
        .appName("IMDb Verify")
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}")
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )


if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 50)
    print("VERIFY SILVER LAYER")
    print("=" * 50)

    for table in TABLES:
        path = f"{SILVER_PATH}/{table}"
        df = spark.read.parquet(path)
        print(f"\n[{table}]")
        print(f"  Rows   : {df.count():,}")
        print(f"  Columns: {df.columns}")
        df.show(3, truncate=True)

    print("\n=== TEST JOIN: movies + movies_genres ===")
    movies = spark.read.parquet(f"{SILVER_PATH}/movies")
    genres = spark.read.parquet(f"{SILVER_PATH}/movies_genres")
    result = (
        movies.join(genres, movies.id == genres.movie_id)
        .groupBy("genre")
        .count()
        .orderBy("count", ascending=False)
    )
    result.show(10)

    spark.stop()