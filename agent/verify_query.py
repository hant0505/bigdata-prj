import os

try:
    from pyspark.sql import SparkSession
except ImportError:
    SparkSession = None

DATA_DIR = "data"


def _register_parquet_tables(spark):
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.lower().endswith(".parquet"):
            continue
        table = os.path.splitext(fname)[0]
        path = os.path.join(DATA_DIR, fname).replace('\\', '/')
        df = spark.read.parquet(path)
        df.createOrReplaceTempView(table)


def _create_spark_session():
    if SparkSession is None:
        return None

    spark = SparkSession.builder.appName("VerifySilverParquet").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def run_query(query, description):
    print("\n" + "="*50)
    print(f"🔍 {description}")
    print("="*50)

    spark = _create_spark_session()
    if spark is None:
        print("❌ pyspark is not installed. Please install pyspark in the agent environment.")
        return

    _register_parquet_tables(spark)

    try:
        df = spark.sql(query)
        rows = df.collect()

        print(f"✅ Số dòng trả về: {len(rows)}")
        for row in rows:
            print(tuple(row))

    except Exception as e:
        print("❌ Lỗi:", e)

    finally:
        spark.stop()


def main():
    print("🧪 VERIFY SILVER PARQUET DATASET\n")

    if not os.path.isdir(DATA_DIR):
        print(f"❌ Không tìm thấy thư mục data: {DATA_DIR}")
        return

    tables = [
        os.path.splitext(f)[0]
        for f in os.listdir(DATA_DIR)
        if f.lower().endswith(".parquet")
    ]

    if not tables:
        print(f"❌ Không tìm thấy parquet files trong {DATA_DIR}")
        return

    print(f"✅ Đã phát hiện các bảng: {tables}")
    first_table = tables[0]

    query1 = f"SELECT COUNT(*) FROM {first_table}"
    run_query(query1, f"Kiểm tra số lượng hàng trong {first_table}")

    if "movies" in tables:
        query2 = "SELECT name, year FROM movies ORDER BY year DESC LIMIT 5"
        run_query(query2, "5 phim mới nhất")
    else:
        run_query(f"SELECT * FROM {first_table} LIMIT 5", f"Sample data từ bảng {first_table}")

    query3 = f"SELECT * FROM {first_table} LIMIT 3"
    run_query(query3, "Top 3 hàng đầu trong bảng đầu tiên")


if __name__ == "__main__":
    main()
