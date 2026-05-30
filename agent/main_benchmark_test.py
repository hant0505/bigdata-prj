"""
SQL Intelligence - Main Pipeline
Run: python main.py
"""
import os
import sys
import csv
import json
import time
import argparse
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

# ── Create Tasks for Each Agent ──────────────────────────────────────────────────
def create_tasks(user_question: str, planner, generator, executor, interpreter):

    task_plan = Task(
        description=f"""
User's question: "{user_question}"

Task:
1. Use the get_database_schema tool to inspect the silver parquet schema in `data/`.
2. Analyze the question and create a detailed query plan including:
   - Tables to use (and reasons)
   - Columns to SELECT
   - Filtering conditions (WHERE)
   - JOIN paths (which tables JOIN via which keys)
   - Aggregations: GROUP BY, ORDER BY, LIMIT
""",
        expected_output=(
            "A structured query plan with: "
            "list of tables, columns, JOIN paths, filtering conditions, aggregations"
        ),
        agent=planner,
    )

    task_generate = Task(
        description="""
Based on the query plan from the Query Planner above,
write a complete SQL SELECT statement for Spark SQL over the silver parquet tables.

Requirements:
- Write only SELECT (no INSERT/UPDATE/DELETE)
- Use correct table and column names according to the silver parquet schema
- JOIN on correct relationships between parquet tables
- Add LIMIT 20 if no LIMIT is specified
- Return only pure SQL
""",
        expected_output="A complete, executable SQL SELECT statement for Spark SQL",
        agent=generator,
        context=[task_plan],
    )

    task_execute = Task(
        description="""
Execute the generated SQL statement:
1. Use the execute_sql tool to run the SQL query
2. Check the results:
   - If there is a SQL error: describe the error in detail
   - If the result is empty (0 rows): note it
   - If successful: confirm and return the results

Return: The executed SQL + full results from the database
""",
        expected_output="SQL execution results: the SQL statement + data returned from the database",
        agent=executor,
        context=[task_generate],
    )

    task_interpret = Task(
        description=f"""
Original user question: "{user_question}"

Based on the results from the SQL Executor above,
write an easy-to-understand answer in English:
1. Answer the question directly
2. Present the main results (top items, important numbers)
3. Provide insights if any
4. Keep it concise, succinct, and friendly
""",
        expected_output="An easy-to-understand English answer for the end user",
        agent=interpreter,
        context=[task_execute],
    )

    return [task_plan, task_generate, task_execute, task_interpret]


# ── Pipeline Runner Function ────────────────────────────────────────────────────────
def run_query(user_question: str) -> dict:
    """
    Run the full SQL Intelligence pipeline for a question.
    Returns dict with: plan, sql, result, answer
    """
    print(f"\n{'='*60}")
    print(f"🔍 QUESTION: {user_question}")
    print(f"{'='*60}\n")

    # SỬA TẠI ĐÂY: Không truyền biến llm tĩnh vào hàm create_agents nữa.
    # Toàn bộ 4 Agents bên trong file agents.py đã được cấu hình tự động gọi hàm xoay vòng key động.
    planner, generator, executor, interpreter = create_agents()
    
    tasks = create_tasks(user_question, planner, generator, executor, interpreter)

    crew = Crew(
        agents=[planner, generator, executor, interpreter],
        tasks=tasks,
        process=Process.sequential,  # Chạy tuần tự: plan -> generate -> execute -> interpret
        verbose=True,
        cache=False                  # Tắt bộ nhớ đệm tự động của CrewAI để tránh lỗi breakpoint
    )

    result = crew.kickoff()

    print(f"\n{'='*60}")
    print("✅ FINAL RESULT:")
    print(f"{'='*60}")
    print(result.raw)

    return {
        "question": user_question,
        "answer": result.raw,
        "tasks_output": [t.output.raw if t.output else "" for t in tasks],
    }


# ── Benchmark Utilities ────────────────────────────────────────────────────────
def clean_sql(sql: str) -> str:
    """Remove markdown fences from generated SQL."""
    if not sql:
        return ""

    sql_clean = sql.strip()
    if "```" in sql_clean:
        lines = sql_clean.split("\n")
        sql_lines = [line for line in lines if not line.strip().startswith("```")]
        sql_clean = "\n".join(sql_lines).strip()

    return sql_clean


def run_sql_raw(sql: str):
    """Run SQL directly on the current SparkSession for benchmark comparison."""
    sql_clean = clean_sql(sql)
    if not sql_clean.upper().startswith("SELECT"):
        return "ERROR: Only SELECT SQL is allowed."

    spark = _get_spark_session()
    if spark is None:
        return "ERROR: Cannot create SparkSession."

    try:
        rows = spark.sql(sql_clean).limit(1000).collect()
        return [tuple(row) for row in rows]
    except Exception as e:
        return f"ERROR: {e}"


def normalize_result(rows):
    """Sort rows to compare execution results independent of row order."""
    if isinstance(rows, list):
        return sorted([str(row) for row in rows])
    return rows


def append_jsonl(path: str, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_benchmark(gold_csv: str, output_jsonl: str = "benchmark_results.jsonl", limit=None, delay: float = 0.0):
    """
    Run benchmark from CSV file with columns: id, question, gold_sql.
    Execution Accuracy = compare Spark result of predicted SQL and gold SQL.
    """
    print(f"\n{'='*60}")
    print("🚀 STARTING CREWAI + SPARK SQL BENCHMARK")
    print(f"{'='*60}")

    if not os.path.exists(gold_csv):
        print(f"Không tìm thấy file benchmark: {gold_csv}")
        return

    with open(gold_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if limit:
        rows = rows[:limit]

    success_count = 0
    correct_count = 0

    for i, row in enumerate(rows, 1):
        question = row.get("question", "").strip()
        gold_sql = row.get("gold_sql", "").strip()
        qid = row.get("id", i)

        if not question:
            continue

        print(f"\n[{i}/{len(rows)}] ID={qid}")
        print(f"Question: {question}")

        start_time = time.time()
        result = run_query(question)
        time_seconds = round(time.time() - start_time, 2)

        tasks_output = result.get("tasks_output", [])
        pred_sql = clean_sql(tasks_output[1]) if len(tasks_output) > 1 else ""

        pred_rows = run_sql_raw(pred_sql) if pred_sql else "ERROR: Empty predicted SQL"
        gold_rows = run_sql_raw(gold_sql) if gold_sql else "ERROR: Empty gold SQL"

        is_success = isinstance(pred_rows, list)
        is_correct = False
        if isinstance(pred_rows, list) and isinstance(gold_rows, list):
            is_correct = normalize_result(pred_rows) == normalize_result(gold_rows)

        if is_success:
            success_count += 1
        if is_correct:
            correct_count += 1

        record = {
            "id": qid,
            "question": question,
            "gold_sql": gold_sql,
            "pred_sql": pred_sql,
            "is_success": is_success,
            "is_correct": is_correct,
            "time_seconds": time_seconds,
            "answer": result.get("answer", ""),
            "pred_rows_preview": str(pred_rows)[:500],
            "gold_rows_preview": str(gold_rows)[:500],
        }
        append_jsonl(output_jsonl, record)

        print(f"Pred SQL: {pred_sql.replace(chr(10), ' ')}")
        if not is_correct:
            print(f"Gold SQL: {gold_sql.replace(chr(10), ' ')}")
            print(f"Pred rows: {str(pred_rows)[:200]}")
            print(f"Gold rows: {str(gold_rows)[:200]}")

        print(f"Status: {'✅ CORRECT' if is_correct else '❌ WRONG'}")
        print(f"Time: {time_seconds}s")

        if delay > 0 and i < len(rows):
            time.sleep(delay)

    total = len(rows)
    print(f"\n{'='*60}")
    print("📊 BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"Answer Rate: {success_count}/{total} ({(success_count/total)*100:.1f}%)")
    print(f"Execution Accuracy: {correct_count}/{total} ({(correct_count/total)*100:.1f}%)")
    print(f"Detailed results saved to: {output_jsonl}")


# ── CLI Demo / Benchmark ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQL Intelligence Main Pipeline")
    parser.add_argument("--benchmark", action="store_true", help="Chạy benchmark từ file CSV")
    parser.add_argument("--gold-csv", type=str, default="gold_sql.csv", help="CSV gồm id,question,gold_sql")
    parser.add_argument("--output-jsonl", type=str, default="benchmark_results.jsonl", help="File lưu kết quả benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số câu benchmark")
    parser.add_argument("--delay", type=float, default=0.0, help="Nghỉ giữa các câu benchmark")
    parser.add_argument("question", nargs="*", help="Câu hỏi test nhanh")
    args = parser.parse_args()

    # Khởi tạo cache schema từ MinIO trước khi chạy pipeline
    initialize_schema_cache()

    if args.benchmark:
        run_benchmark(
            gold_csv=args.gold_csv,
            output_jsonl=args.output_jsonl,
            limit=args.limit,
            delay=args.delay,
        )
    else:
        # Demo questions — change the question here to test
        demo_questions = [
            "Mỗi năm có bao nhiêu bộ phim được phát hành? Chỉ hiển thị những năm có trên 1000 bộ phim.",
        ]

        question = demo_questions[0]

        # Or input from command line: python main.py "your question"
        if args.question:
            question = " ".join(args.question)

        run_query(question)
