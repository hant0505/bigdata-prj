from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from config import *


def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("IMDb ETL - Silver Layer")
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


def clean_movies(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["id"])
        .filter(F.col("id").isNotNull())
        .withColumn("name", F.trim(F.col("name")))
        .withColumn("year", F.col("year").cast("integer"))
        .withColumn("rank", F.col("rank").cast("float"))
        .filter(F.col("year").isNull() | F.col("year").between(1888, 2030))
    )


def clean_actors(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["id"])
        .filter(F.col("id").isNotNull())
        .withColumn("first_name", F.trim(F.col("first_name")))
        .withColumn("last_name", F.trim(F.col("last_name")))
        .withColumn("full_name",
                    F.concat_ws(" ", F.col("first_name"), F.col("last_name")))
    )


def clean_directors(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["id"])
        .filter(F.col("id").isNotNull())
        .withColumn("first_name", F.trim(F.col("first_name")))
        .withColumn("last_name", F.trim(F.col("last_name")))
        .withColumn("full_name",
                    F.concat_ws(" ", F.col("first_name"), F.col("last_name")))
    )


def clean_roles(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["actor_id", "movie_id", "role"])
        .filter(F.col("actor_id").isNotNull() & F.col("movie_id").isNotNull())
        .withColumn("role", F.trim(F.col("role")))
    )


def clean_movies_genres(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["movie_id", "genre"])
        .filter(F.col("movie_id").isNotNull() & F.col("genre").isNotNull())
        .withColumn("genre", F.trim(F.col("genre")))
    )


def clean_movies_directors(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["director_id", "movie_id"])
        .filter(F.col("director_id").isNotNull() & F.col("movie_id").isNotNull())
    )


def clean_directors_genres(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["director_id", "genre"])
        .filter(F.col("director_id").isNotNull())
        .withColumn("genre", F.trim(F.col("genre")))
        .withColumn("prob", F.col("prob").cast("float"))
        .filter(F.col("prob").isNull() | F.col("prob").between(0.0, 1.0))
    )


TRANSFORM_MAP = {
    "movies":           clean_movies,
    "actors":           clean_actors,
    "directors":        clean_directors,
    "roles":            clean_roles,
    "movies_genres":    clean_movies_genres,
    "movies_directors": clean_movies_directors,
    "directors_genres": clean_directors_genres,
}


def process_silver(spark, table_name: str):
    print(f"[SILVER] Processing: {table_name}")

    bronze_path = f"{BRONZE_PATH}/{table_name}"
    df_raw = spark.read.parquet(bronze_path)
    raw_count = df_raw.count()
    print(f"  -> Bronze rows: {raw_count:,}")

    transform_fn = TRANSFORM_MAP[table_name]
    df_clean = transform_fn(df_raw)
    silver_count = df_clean.count()
    print(f"  -> Silver rows: {silver_count:,} (dropped {raw_count - silver_count:,})")

    silver_path = f"{SILVER_PATH}/{table_name}"
    df_clean.write.mode("overwrite").parquet(silver_path)
    print(f"  Done: {silver_path}\n")


if __name__ == "__main__":
    spark = create_spark_session()

    for table in TABLES:
        process_silver(spark, table)

    print("=== SILVER LAYER COMPLETE ===")
    spark.stop()