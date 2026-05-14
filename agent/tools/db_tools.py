from crewai.tools import tool
import sqlite3

@tool
def get_database_schema():
    """
    Lấy toàn bộ schema của database SQLite (tên bảng và các cột).
    Trả về dạng string để agent có thể hiểu cấu trúc database.
    """
    conn = sqlite3.connect("data/chinook.db")
    cursor = conn.cursor()

    schema = ""

    tables = cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table';
    """).fetchall()

    """
    PRAGMA foreign_key_list(table) trả về: (id, seq, table, from, to, on_update, on_delete, match)
    - id: số thứ tự của FK trong bảng
    - seq: thứ tự của FK nếu có nhiều FK trong cùng bảng
    - table: tên bảng được tham chiếu (bảng đích)
    - from: cột trong bảng hiện tại (bảng nguồn)
    - to: cột trong bảng đích (bảng được tham chiếu)
    - on_update: hành động khi cột đích bị update (CASCADE, SET NULL, NO ACTION, v.v.)
    - on_delete: hành động khi cột đích bị delete (CASCADE, SET NULL, NO ACTION, v.v.)
    - match: điều kiện match (thường là NONE)
    """
    for (table_name,) in tables:
        schema += f"\n{table_name}:\n"

        # Get columns
        columns = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()

        for col in columns:
            schema += f"  - {col[1]} ({col[2]})\n"

        # 📌 Foreign Keys (THÊM Ở ĐÂY)
        fk_info = cursor.execute(
            f"PRAGMA foreign_key_list({table_name});"
        ).fetchall()

        for fk in fk_info:
            schema += f"  -> FK: {fk[3]} → {fk[2]}.{fk[4]}\n"

    conn.close()
    return schema