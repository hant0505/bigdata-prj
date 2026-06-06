"""
SQL Intelligence - Main Pipeline
Run: python main.py
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

# Khắc phục đường dẫn hệ thống để nhận diện đúng thư mục agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Crew, Task, Process
from agents.agents import create_agents
from dotenv import load_dotenv

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
    print(f"QUESTION: {user_question}")
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
    print("FINAL RESULT:")
    print(f"{'='*60}")
    print(result.raw)

    return {
        "question": user_question,
        "answer": result.raw,
        "tasks_output": [t.output.raw if t.output else "" for t in tasks],
    }


# ── CLI Demo ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Demo questions — change the question here to test
    demo_questions = [
        "Mỗi năm có bao nhiêu bộ phim được phát hành? Chỉ hiển thị những năm có trên 1000 bộ phim.",
    ]

    question = demo_questions[0]

    # Or input from command line: python main.py "your question"
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])

    run_query(question)
