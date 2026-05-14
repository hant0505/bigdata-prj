import sqlite3
import os

DB_PATH = "data/chinook.db"   # chỉnh lại nếu path khác

def check_database():
    print("🔍 Checking database...")

    # 1. Check file tồn tại
    if not os.path.exists(DB_PATH):
        print(f"❌ Không tìm thấy file DB: {DB_PATH}")
        return

    print(f"✅ Tìm thấy DB tại: {DB_PATH}")

    # 2. Connect DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 3. List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("\n📋 Danh sách tables:")
    for table in tables:
        print(f"- {table[0]}")

    # 4. Check bảng Artist có tồn tại không
    table_names = [t[0] for t in tables]

    if "artists" in table_names:
        print("\n✅ Có bảng Artist")

        # 5. Test query đơn giản
        cursor.execute("SELECT * FROM artists LIMIT 5;")
        rows = cursor.fetchall()

        print("\n🎵 Sample data từ Artist:")
        for row in rows:
            print(row)
    else:
        print("\n❌ KHÔNG có bảng Artist -> DB sai hoặc rỗng")

    conn.close()


if __name__ == "__main__":
    check_database()