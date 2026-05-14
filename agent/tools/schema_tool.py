"""
Tool: Schema Loader
Nhiệm vụ: Load schema Chinook và cung cấp cho agents
"""
import sqlite3
from crewai.tools import BaseTool
from pydantic import Field

DB_PATH = "data/chinook.db"

SCHEMA_DESCRIPTION = """
Chinook Database Schema (Digital Music Store):

artists (ArtistId PK, Name)
albums (AlbumId PK, Title, ArtistId FK->artists)
tracks (TrackId PK, Name, AlbumId FK->albums, GenreId FK->genres, UnitPrice)
customers (CustomerId PK, FirstName, LastName, Country, Email)
invoices (InvoiceId PK, CustomerId FK->customers, InvoiceDate, Total)
invoice_items (InvoiceLineId PK, InvoiceId FK->invoices, TrackId FK->tracks, UnitPrice, Quantity)


Key relationships (JOIN paths):
- Revenue by Artist: artists -> albums -> tracks -> invoice_items -> invoices
- Genre analysis:    genres -> tracks
- Customer revenue:  customers -> invoices -> invoice_items
"""

class GetSchemaTool(BaseTool):
    name: str = "get_database_schema"
    description: str = "Lấy schema đầy đủ của Chinook database để lập kế hoạch truy vấn"

    def _run(self) -> str:
        return SCHEMA_DESCRIPTION


class ExecuteSQLTool(BaseTool):
    name: str = "execute_sql"
    description: str = "Thực thi câu lệnh SQL SELECT trên Chinook database và trả về kết quả"
    db_path: str = Field(default=DB_PATH)

    def _run(self, sql: str) -> str:
        # Bảo mật: chỉ cho phép SELECT
        sql_clean = sql.strip()
        # Loại bỏ markdown code block nếu có
        if "```" in sql_clean:
            lines = sql_clean.split("\n")
            sql_lines = [l for l in lines if not l.startswith("```")]
            sql_clean = "\n".join(sql_lines).strip()

        if not sql_clean.upper().startswith("SELECT"):
            return "ERROR: Chỉ cho phép câu lệnh SELECT. Không thể thực thi."

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql_clean)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()

            if not rows:
                return "Kết quả: 0 dòng trả về (empty result)"

            # Format kết quả dạng bảng text
            result = f"Columns: {columns}\n"
            result += f"Rows ({len(rows)} total):\n"
            for row in rows[:20]:  # Giới hạn 20 dòng hiển thị
                result += f"  {dict(zip(columns, row))}\n"
            return result

        except sqlite3.Error as e:
            return f"SQL ERROR: {str(e)}\nSQL was: {sql_clean}"
