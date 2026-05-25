import os

try:
    from pyspark.sql import SparkSession
except ImportError:
    SparkSession = None

DATA_DIR = "data"


def _repo_parquet_files():
    return sorted(
        f for f in os.listdir(DATA_DIR)
        if os.path.isfile(os.path.join(DATA_DIR, f)) and f.lower().endswith(".parquet")
    )


def _create_spark_session():
    if SparkSession is None:
        return None

    spark = SparkSession.builder.appName("SilverParquetCheck").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def check_database():
    print("🔍 Checking silver parquet dataset...")

    if SparkSession is None:
        print("❌ pyspark is not installed. Please install pyspark in the agent environment.")
        return

    if not os.path.isdir(DATA_DIR):
        print(f"❌ Không tìm thấy thư mục data: {DATA_DIR}")
        return

    files = _repo_parquet_files()
    if not files:
        print(f"❌ Không tìm thấy file parquet trong {DATA_DIR}")
        return

    print(f"✅ Tìm thấy {len(files)} parquet files trong {DATA_DIR}:")
    for fname in files:
        print(f"- {fname}")

    spark = _create_spark_session()
    if spark is None:
        print("❌ Không thể tạo SparkSession.")
        return

    for fname in files:
        table = os.path.splitext(fname)[0]
        path = os.path.join(DATA_DIR, fname).replace('\\', '/')
        df = spark.read.parquet(path)
        df.createOrReplaceTempView(table)

    sample_table = "movies" if "movies.parquet" in files else os.path.splitext(files[0])[0]
    print(f"\n📌 Sample data from {sample_table}")
    df_sample = spark.sql(f"SELECT * FROM {sample_table} LIMIT 5")
    df_sample.show(5, truncate=False)

    spark.stop()


if __name__ == "__main__":
    check_database()
