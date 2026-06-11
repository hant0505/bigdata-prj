"""
Agents Definition - SQL Intelligence System
"""
from crewai import Agent
from tools.schema_tool import GetSchemaTool, ExecuteSQLTool
from config import get_llm # Vẫn giữ import độc lập từ file config

def create_agents():
    schema_tool = GetSchemaTool()
    execute_tool = ExecuteSQLTool()

    # ── Agent 1: Schema-Aware Query Planner ──────────────────────────────────
    planner = Agent(
        role="Schema-Aware Query Planner",
        goal=(
            "Analyze the user's natural language question and create a detailed query plan that precisely identifies: "
            "which tables to use, which columns to retrieve, filtering conditions, JOIN operations, and necessary aggregations."
        ),
        backstory=(
            "You are a data analysis expert with deep knowledge of the silver parquet dataset. "
            "Your task is to read the user's question, consult the schema, and outline a clear step-by-step query plan. "
            "Your output must include: (1) Tables to use, (2) Columns to retrieve, (3) WHERE conditions, (4) JOIN paths, (5) GROUP BY/ORDER BY if needed."
        ),
        tools=[schema_tool],
        # SỬA LẠI THÀNH: get_llm() -> Mỗi Agent sẽ tự bốc 1 key riêng!
        llm=get_llm(), 
        verbose=True,
    )

    # ── Agent 2: SQL Generator ────────────────────────────────────────────────
    generator = Agent(
        role="SQL Generator",
        goal=(
            "Based on the plan from the Query Planner, write a complete, accurate, and optimized SQL SELECT statement for Spark SQL over parquet tables."
        ),
        backstory=(
            "You are a professional SQL engineer. You receive the plan from the Planner and convert it into a complete SQL statement. "
            "Always adhere to: (1) Write only SELECT statements, (2) Use correct table/column names from the schema, "
            "(3) JOIN on correct relationships between parquet tables, (4) Add LIMIT 20 if no LIMIT is specified. Return only the pure SQL statement, no explanations."
        ),
        tools=[schema_tool],
        # Gọi hàm get_llm() để sinh ra 1 key mới cho Generator
        llm=get_llm(), 
        verbose=True,
    )

    # ── Agent 3: SQL Executor & QA ────────────────────────────────────────────
    executor = Agent(
        role="SQL Executor and QA",
        goal=(
            "Execute the SQL query on the database and validate the results. "
            "If there are errors, analyze them and request corrections. "
            "If successful, confirm the results are valid."
        ),
        backstory=(
            "You are a QA engineer specializing in SQL testing. "
            "You receive the SQL from the Generator, execute it, and evaluate: "
            "(1) Are there syntax errors? (2) Are the results reasonable? (3) Does it return zero rows? "
            "If there are issues, describe the errors clearly for the Generator to fix."
        ),
        tools=[execute_tool],
        # Lại tiếp tục bốc 1 key mới cho Executor
        llm=get_llm(), 
        verbose=True,
    )

    # ── Agent 4: Data Interpreter ─────────────────────────────────────────────
    interpreter = Agent(
        role="Data Interpreter",
        goal=(
            "Summarize the numerical results and translate them into a natural Vietnamese response that is easy to understand for the end user."
        ),
        backstory=(
            "You are a data communication expert. "
            "You take dry numerical tables and turn them into friendly, insightful, easy-to-understand answers. "
            "Always respond in Vietnamese, summarize the key results, and highlight notable points."
            "Keep SQL keywords, table names, column names, and proper nouns unchanged when needed."
        ),
        tools=[],
        llm=get_llm(), 
        verbose=True,
    )

    return planner, generator, executor, interpreter