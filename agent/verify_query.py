import sqlite3

DB_PATH = "data/chinook.db"

def run_query(query, description):
    print("\n" + "="*50)
    print(f"🔍 {description}")
    print("="*50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        print(f"✅ Số dòng trả về: {len(rows)}")
        for row in rows:
            print(row)

    except Exception as e:
        print("❌ Lỗi:", e)

    finally:
        conn.close()


def main():
    print("🧪 VERIFY DATABASE\n")

    # 1. Check có data không
    query1 = "SELECT COUNT(*) FROM invoice_items;"
    run_query(query1, "Kiểm tra số lượng invoice_items")

    # 2. Check doanh thu Iron Maiden
    query2 = """
    SELECT
      artists.Name,
      SUM(invoice_items.UnitPrice * invoice_items.Quantity) AS revenue
    FROM artists
    JOIN albums ON artists.ArtistId = albums.ArtistId
    JOIN tracks ON albums.AlbumId = tracks.AlbumId
    JOIN invoice_items ON tracks.TrackId = invoice_items.TrackId
    WHERE artists.Name = 'Iron Maiden';
    """
    run_query(query2, "Doanh thu Iron Maiden")

    # 3. Check full top 3 (so sánh với pipeline)
    query3 = """
    SELECT
      artists.Name,
      SUM(invoice_items.UnitPrice * invoice_items.Quantity) AS revenue
    FROM artists
    JOIN albums ON artists.ArtistId = albums.ArtistId
    JOIN tracks ON albums.AlbumId = tracks.AlbumId
    JOIN invoice_items ON tracks.TrackId = invoice_items.TrackId
    GROUP BY artists.ArtistId, artists.Name
    ORDER BY revenue DESC
    LIMIT 3;
    """
    run_query(query3, "Top 3 nghệ sĩ doanh thu cao nhất")


if __name__ == "__main__":
    main()