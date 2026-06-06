"""
Tools for reading the local silver parquet dataset.

The files in data/ are Spark part files, so table names are mapped by the
stable UUID embedded in each parquet filename.
"""
import os
from glob import glob
from typing import Type

import duckdb
import pyarrow.parquet as pq
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


TABLE_PATTERNS = {
    "directors_genres": "*30901510-7c4d-4c68-8058-98632fe944c7*.parquet",
    "directors": "*3387f29a-d9c5-40e8-93f9-888ea31ab6bd*.parquet",
    "movies_genres": "*6bca7e71-96c2-4013-83ff-fb3a146e81f3*.parquet",
    "movies": "*7bc5ca87-6478-4108-ad63-950e6c7ff4f8*.parquet",
    "actors": "*86b0f2f0-8a70-4e65-8c87-a5cd56eba6af*.parquet",
    "movies_directors": "*a401de7b-efa5-430d-a522-d9ed5ddcfbd0*.parquet",
    "roles": "*e1bc7189-070b-419a-8804-08dcd75ad41a*.parquet",
}


def _repo_data_dir():
    this = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.dirname(os.path.dirname(this))
    return os.path.join(repo_root, "data")


def _table_files(data_dir: str, table: str) -> list[str]:
    pattern = TABLE_PATTERNS[table]
    return sorted(glob(os.path.join(data_dir, pattern)))


def _register_views(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    for table in TABLE_PATTERNS:
        files = _table_files(data_dir, table)
        if not files:
            continue
        file_list = ", ".join(repr(path.replace("\\", "/")) for path in files)
        con.execute(
            f"CREATE OR REPLACE VIEW {table} AS "
            f"SELECT * FROM read_parquet([{file_list}])"
        )


class GetSchemaInput(BaseModel):
    table_filter: str | None = Field(
        default=None,
        description="Optional table name substring to filter schema output.",
    )


class ExecuteSQLInput(BaseModel):
    sql: str = Field(description="A SELECT SQL query to execute.")


class GetSchemaTool(BaseTool):
    name: str = "get_database_schema"
    description: str = "Get the schema of local silver parquet tables."
    args_schema: Type[BaseModel] = GetSchemaInput

    def _run(self, table_filter: str | None = None, **kwargs) -> str:
        data_dir = _repo_data_dir()
        if not os.path.isdir(data_dir):
            return f"Data directory not found: {data_dir}"

        schema_lines = []
        for table in sorted(TABLE_PATTERNS):
            if table_filter and table_filter.lower() not in table.lower():
                continue

            files = _table_files(data_dir, table)
            if not files:
                schema_lines.append(f"{table}: ERROR no parquet files found")
                continue

            try:
                schema = pq.read_schema(files[0])
                columns = [field.name for field in schema]
                schema_lines.append(f"{table}: {columns}")
            except Exception as exc:
                schema_lines.append(f"{table}: ERROR reading schema ({exc})")

        if not schema_lines:
            return f"No matching parquet tables found in {data_dir}"

        return "\n".join(schema_lines)


class ExecuteSQLTool(BaseTool):
    name: str = "execute_sql"
    description: str = "Execute a SELECT SQL query on local silver parquet tables."
    args_schema: Type[BaseModel] = ExecuteSQLInput
    data_dir: str = Field(default_factory=_repo_data_dir)

    def _run(self, sql: str, **kwargs) -> str:
        sql_clean = sql.strip()
        if "```" in sql_clean:
            lines = sql_clean.split("\n")
            sql_lines = [line for line in lines if not line.startswith("```")]
            sql_clean = "\n".join(sql_lines).strip()

        if not sql_clean.upper().startswith("SELECT"):
            return "ERROR: Only SELECT statements are allowed."

        try:
            con = duckdb.connect(database=":memory:")
            _register_views(con, self.data_dir)

            df_result = con.execute(sql_clean).fetchdf()
            if df_result.empty:
                return "Result: 0 rows returned (empty result)"

            limited = df_result.head(20)
            return (
                f"Columns: {list(df_result.columns)}\n"
                f"Rows ({len(df_result)} returned, showing {len(limited)}):\n"
                f"{limited.to_string(index=False)}"
            )
        except Exception as exc:
            return f"SQL ERROR: {exc}\nSQL was: {sql_clean}"
