"""
SQL Intelligence - Main Pipeline + Benchmark
Run:
  python main.py --question "your question"
  python main.py --benchmark --gold-csv imdb_gold.csv --limit 10
CSV format: id,question,gold_sql
"""
import os
import sys
import time
import csv
import json
import argparse
from typing import Any, List

# fix khi lam Dockerfile
import pysqlite3
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

# Khắc phục đường dẫn hệ thống để nhận diện đúng thư mục agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Task, Process
from agents.agents import create_agents
from dotenv import load_dotenv
from tools.schema_tool import initialize_schema_cache, _get_spark_session

load_dotenv()


# ── Helpers ─────────────────────────────────────────────────────────────────────
def clean_sql(sql: str) -> str:
    """Remove markdown fences and keep SELECT SQL only."""
    if not sql:
        return ""

    sql_clean = sql.strip()

    if "```" in sql_clean:
        lines = sql_clean.splitlines()
        lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]
        sql_clean = "\n".join(lines).strip()

    # Some agents may add small prefixes. Try to cut from SELECT.
    upper_sql = sql_clean.upper()
    select_pos = upper_sql.find("SELECT")
    if select_pos >= 0:
        sql_clean = sql_clean[select_pos:].strip()

    # Remove trailing semicolon for safety
    if sql_clean.endswith(";"):
        sql_clean = sql_clean[:-1].strip()

    return sql_clean


def append_jsonl(path: str, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_result(rows: Any) -> Any:
    """
    Normalize Spark rows for execution-accuracy comparison.
    Sorting avoids wrong grading caused only by row order.
    """
    if isinstance(rows, list):
        return sorted([str(tuple(row)) for row in rows])
    return rows


def run_spark_sql_collect(sql: str, limit: int = 10000) -> Any:
    """
    Execute SQL directly on the existing SparkSession for benchmark grading.
    This assumes initialize_schema_cache() has already registered Temp Views.
    """
    sql_clean = clean_sql(sql)

    if not sql_clean.upper().startswith("SELECT"):
        return f"ERROR: Only SELECT is allowed. SQL was: {sql_clean}"

    spark = _get_spark_session()
    if spark is None:
        return "ERROR: Cannot create SparkSession."

    try:
        rows = spark.sql(sql_clean).limit(limit).collect()
        return [tuple(row) for row in rows]
    except Exception as e:
        return f"SQL ERROR: {e}\nSQL was: {sql_clean}"


# ── Create Tasks For Each Agent ─────────────────────────────────────────────────
def create_tasks(user_question: str, planner, generator, executor, interpreter):
    task_plan = Task(
        description=f"""
User's question: "{user_question}"

Task:
1. Use the get_database_schema tool to inspect the silver parquet schema.
2. Analyze the question and create a detailed query plan including:
   - Tables to use and reasons
   - Columns to SELECT
   - Filtering conditions
   - JOIN paths
   - Aggregations: GROUP BY, ORDER BY, LIMIT
""",
        expected_output=(
            "A structured query plan with tables, columns, JOIN paths, "
            "filtering conditions, and aggregations."
        ),
        agent=planner,
    )

    task_generate = Task(
        description="""
Based on the query plan from the Query Planner above,
write a complete SQL SELECT statement for Spark SQL over the silver parquet tables.

Requirements:
- Write only SELECT. No INSERT/UPDATE/DELETE.
- Use correct table and column names according to the silver parquet schema.
- JOIN on correct relationships between parquet tables.
- Add LIMIT 20 if no LIMIT is specified.
- Return only pure SQL. No markdown, no explanation.
""",
        expected_output="A complete executable Spark SQL SELECT statement.",
        agent=generator,
        context=[task_plan],
    )

    task_execute = Task(
        description="""
Execute the generated SQL statement:
1. Use the execute_sql tool to run the SQL query.
2. Check the results:
   - If there is a SQL error: describe the error.
   - If the result is empty: note it.
   - If successful: confirm and return the results.

Return: the executed SQL and the query result.
""",
        expected_output="SQL execution result: SQL statement and returned data.",
        agent=executor,
        context=[task_generate],
    )

    task_interpret = Task(
        description=f"""
Original user question: "{user_question}"

Based on the SQL Executor result above, write an easy-to-understand answer in English:
1. Answer directly.
2. Present the main result.
3. Keep it concise.
""",
        expected_output="A concise natural language answer.",
        agent=interpreter,
        context=[task_execute],
    )

    return [task_plan, task_generate, task_execute, task_interpret]


# ── Pipeline Runner ─────────────────────────────────────────────────────────────
def run_query(user_question: str) -> dict:
    """
    Run the full SQL Intelligence pipeline for one question.
    Returns dict with question, answer, generated SQL, task outputs, status, and runtime.
    """
    print(f"\n{'=' * 60}")
    print(f"🔍 QUESTION: {user_question}")
    print(f"{'=' * 60}\n")

    start_time = time.time()

    planner, generator, executor, interpreter = create_agents()
    tasks = create_tasks(user_question, planner, generator, executor, interpreter)

    crew = Crew(
        agents=[planner, generator, executor, interpreter],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        cache=False,
    )

    try:
        result = crew.kickoff()
        status = "success"
        answer = result.raw
    except Exception as e:
        status = "error"
        answer = f"PIPELINE ERROR: {e}"

    elapsed = round(time.time() - start_time, 2)

    task_outputs = [t.output.raw if t.output else "" for t in tasks]
    pred_sql = clean_sql(task_outputs[1]) if len(task_outputs) > 1 else ""

    print(f"\n{'=' * 60}")
    print("✅ FINAL RESULT:")
    print(f"{'=' * 60}")
    print(answer)
    print(f"⏱ Time: {elapsed}s")

    return {
        "question": user_question,
        "answer": answer,
        "pred_sql": pred_sql,
        "tasks_output": task_outputs,
        "status": status,
        "time_seconds": elapsed,
    }


# ── Benchmark ───────────────────────────────────────────────────────────────────
def run_benchmark(
    gold_csv: str,
    limit: int | None = None,
    delay: float = 0.0,
    output_jsonl: str = "benchmark_crewai_spark_results.jsonl",
) -> None:
    """
    Run benchmark from CSV with columns: id,question,gold_sql.
    Metric: Execution Accuracy = compare result of predicted SQL vs gold SQL.
    """
    print("=" * 60)
    print("🚀 BẮT ĐẦU CHẠY CREWAI + SPARK SQL BENCHMARK")
    print("=" * 60)

    if not os.path.exists(gold_csv):
        print(f"Không tìm thấy file gold CSV: {gold_csv}")
        return

    # One SparkSession + one Temp View registration for the whole benchmark.
    initialize_schema_cache()

    with open(gold_csv, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if limit is not None:
        rows = rows[:limit]

    total = len(rows)
    success_count = 0
    correct_count = 0

    # Start fresh output file
    if os.path.exists(output_jsonl):
        os.remove(output_jsonl)

    for i, row in enumerate(rows, 1):
        qid = row.get("id", str(i))
        question = row.get("question", "").strip()
        gold_sql = row.get("gold_sql", "").strip()

        if not question:
            continue

        print(f"\n[{i}/{total}] ID={qid}")
        print(f"Hỏi: {question}")

        result = run_query(question)
        pred_sql = clean_sql(result.get("pred_sql", ""))

        # Grade by executing both predicted SQL and gold SQL on Spark.
        pred_rows = run_spark_sql_collect(pred_sql)
        gold_rows = run_spark_sql_collect(gold_sql)

        is_correct = False
        if isinstance(pred_rows, list) and isinstance(gold_rows, list):
            is_correct = normalize_result(pred_rows) == normalize_result(gold_rows)

        if result["status"] == "success" and pred_sql:
            success_count += 1

        if is_correct:
            correct_count += 1
            accuracy_status = "✅ ĐÚNG"
        else:
            accuracy_status = "❌ SAI"

        record = {
            "index": i,
            "id": qid,
            "question": question,
            "gold_sql": gold_sql,
            "pred_sql": pred_sql,
            "is_correct": is_correct,
            "status": result["status"],
            "time_seconds": result["time_seconds"],
            "answer": result["answer"],
            "pred_result_preview": str(pred_rows)[:500],
            "gold_result_preview": str(gold_rows)[:500],
        }
        append_jsonl(output_jsonl, record)

        print(f"=> SQL AI   : {pred_sql.replace(chr(10), ' ')}")
        if not is_correct:
            print(f"=> SQL Gold : {gold_sql.replace(chr(10), ' ')}")
            print(f"   [!] Data AI   : {str(pred_rows)[:300]}")
            print(f"   [!] Data Gold : {str(gold_rows)[:300]}")

        print(f"=> Chấm điểm: {accuracy_status}")
        print(f"=> Thời gian : {result['time_seconds']}s")

        if delay > 0 and i < total:
            time.sleep(delay)

    print("\n" + "=" * 60)
    print("📊 BÁO CÁO TỔNG KẾT BENCHMARK")
    print("=" * 60)
    print(f"| Answer Rate        : {success_count}/{total} ({(success_count / total) * 100:.1f}%)")
    print(f"| Execution Accuracy : {correct_count}/{total} ({(correct_count / total) * 100:.1f}%)")
    print(f"Kết quả chi tiết lưu tại: {output_jsonl}")


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CrewAI + Spark SQL Intelligence")
    parser.add_argument("--question", type=str, default=None, help="Chạy 1 câu hỏi trực tiếp")
    parser.add_argument("--benchmark", action="store_true", help="Chạy benchmark từ CSV")
    parser.add_argument("--gold-csv", type=str, default="gold_sql.csv", help="CSV gồm id,question,gold_sql")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số câu benchmark")
    parser.add_argument("--delay", type=float, default=0.0, help="Nghỉ giữa các câu benchmark")
    parser.add_argument("--output-jsonl", type=str, default="benchmark_crewai_spark_results.jsonl")
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark(
            gold_csv=args.gold_csv,
            limit=args.limit,
            delay=args.delay,
            output_jsonl=args.output_jsonl,
        )
    elif args.question:
        initialize_schema_cache()
        run_query(args.question)
    else:
        initialize_schema_cache()
        demo_question = "Mỗi năm có bao nhiêu bộ phim được phát hành? Chỉ hiển thị những năm có trên 1000 bộ phim."
        run_query(demo_question)
