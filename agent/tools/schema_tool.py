"""
Tool: Schema Loader for silver parquet files
This tool exposes the schema (table names and columns) by scanning the repository
`data/` directory for `.parquet` files and lets agents execute `SELECT` SQL
against those files using PySpark.
"""
import os
from crewai.tools import BaseTool
from duckdb import table
from pydantic import Field

try:
    from pyspark.sql import SparkSession
except Exception:
    SparkSession = None


TABLES = {
    "movies": "s3a://imdb/silver/movies",
    "actors": "s3a://imdb/silver/actors",
    "directors": "s3a://imdb/silver/directors",
    "movies_genres": "s3a://imdb/silver/movies_genres",
    "movies_directors": "s3a://imdb/silver/movies_directors",
    "roles": "s3a://imdb/silver/roles",
    "directors_genres": "s3a://imdb/silver/directors_genres",
}

def _repo_data_dir():
    # repo root is parent of agent/
    this = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.dirname(os.path.dirname(this))
    return os.path.join(repo_root, "data")


def _get_spark_session():
    if SparkSession is None:
        return None

    spark = (
        SparkSession.builder
        .appName("BigdataSchemaTool")
        .master(os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077"))

        # JAR S3A
        .config(
            "spark.jars",
            "/spark/jars/hadoop-aws-3.3.2.jar,"
            "/spark/jars/aws-java-sdk-bundle-1.11.1026.jar"
        )

        #  MinIO / S3A
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "admin"))
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "12345678"))
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")

        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark

#Cache schema vào RAM của các Worker Nodes để tăng tốc độ truy vấn sau này
# 2. Hàm nạp Cache Schema từ MinIO lên RAM
def initialize_schema_cache():
    spark = _get_spark_session()
    
    if spark is None:
        print("Lỗi: Không tìm thấy thư viện PySpark!")
        return

    print("Đang nạp Schema từ MinIO vào Cache của Spark...")
    for table_name, s3_path in TABLES.items():
        # Đọc qua giao thức S3A
        df = spark.read.parquet(s3_path)
        
        # Đăng ký View để Agent có thể viết Spark SQL
        df.createOrReplaceTempView(table_name)
        
        # Đưa vào Cache
        df.cache() 
        df.limit(1).count() 
    print("Nạp Schema từ MinIO thành công! Spark Session đã sẵn sàng.")

class GetSchemaTool(BaseTool):
    name: str = "get_database_schema"
    description: str = "Lấy schema của các bảng trong silver layer (parquet files) bằng PySpark"

    def _run(self, **kwargs) -> str:
        data_dir = _repo_data_dir()
        if not os.path.isdir(data_dir):
            return f"Data directory not found: {data_dir}"

        if SparkSession is None:
            return "PySpark không được cài đặt. Vui lòng cài pyspark trong môi trường agent."

        spark = _get_spark_session()
        if spark is None:
            return "Không thể tạo SparkSession."

        schema_lines = []
        # Sua de lay loading parquet tu MinIO thay vi local data dir
        for table, path in TABLES.items():
            try:
                df = spark.read.parquet(path)
                columns = [field.name for field in df.schema.fields]
                schema_lines.append(f"{table}: {columns}")
            except Exception as e:
                schema_lines.append(f"{table}: ERROR reading schema ({e})")

        if not schema_lines:
            return f"No parquet files found in {data_dir}"

        return "\n".join(schema_lines)


class ExecuteSQLTool(BaseTool):
    name: str = "execute_sql"
    description: str = "Thực thi câu lệnh SQL SELECT trên dữ liệu Silver Layer bằng PySpark"
    data_dir: str = Field(default_factory=_repo_data_dir)

    def _run(self, sql: str, **kwargs) -> str:
        if SparkSession is None:
            return "PySpark không được cài đặt. Vui lòng cài pyspark trong môi trường agent."

        sql_clean = sql.strip()
        if "```" in sql_clean:
            lines = sql_clean.split("\n")
            sql_lines = [l for l in lines if not l.startswith("```")]
            sql_clean = "\n".join(sql_lines).strip()

        if not sql_clean.upper().startswith("SELECT"):
            return "ERROR: Chỉ cho phép câu lệnh SELECT."

        spark = _get_spark_session()
        if spark is None:
            return "Không thể tạo SparkSession."

        try:
            for table, path in TABLES.items():
                try:
                    df = spark.read.parquet(path)
                    df.createOrReplaceTempView(table)
                except Exception as e:
                    return f"ERROR loading table {table}: {e}"

            df_result = spark.sql(sql_clean)
            columns = df_result.columns
            rows = df_result.limit(1000).collect()

            if not rows:
                return "Kết quả: 0 dòng trả về (empty result)"

            result = f"Columns: {columns}\n"
            result += f"Rows ({len(rows)} returned):\n"
            for row in rows[:20]:
                result += f"  {dict(zip(columns, row))}\n"
            return result

        except Exception as e:
            return f"SQL ERROR: {e}\nSQL was: {sql_clean}"
