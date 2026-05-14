"""
SQL Intelligence - Streamlit UI
Chạy: streamlit run ui/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from main import run_query, get_llm
from tools.schema_tool import ExecuteSQLTool

# ── Cấu hình trang ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SQL Intelligence",
    page_icon="🎵",
    layout="wide",
)

st.title("🎵 SQL Intelligence")
st.caption("Hỏi về dữ liệu Chinook bằng tiếng Việt hoặc tiếng Anh — không cần biết SQL")

# ── Sidebar: Schema viewer ────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Database Schema")
    st.code("""
Artist      (ArtistId, Name)
Album       (AlbumId, Title, ArtistId)
Genre       (GenreId, Name)
Track       (TrackId, Name, AlbumId, GenreId, UnitPrice)
Customer    (CustomerId, FirstName, LastName, Country)
Invoice     (InvoiceId, CustomerId, InvoiceDate, Total)
InvoiceLine (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)
    """, language="text")

    st.header("💡 Câu hỏi mẫu")
    sample_questions = [
        "Top 3 nghệ sĩ có doanh thu cao nhất?",
        "Thể loại nhạc nào có nhiều bài hát nhất?",
        "Khách hàng từ quốc gia nào chi tiêu nhiều nhất?",
        "Liệt kê tất cả album của AC/DC",
        "Tổng doanh thu theo từng quốc gia?",
    ]
    for q in sample_questions:
        if st.button(q, key=q, use_container_width=True):
            st.session_state["input_question"] = q

# ── Chat history ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ── Input ─────────────────────────────────────────────────────────────────────
default_val = st.session_state.pop("input_question", "")
user_question = st.text_input(
    "💬 Nhập câu hỏi của bạn:",
    value=default_val,
    placeholder="VD: Top 5 nghệ sĩ có doanh thu cao nhất?",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 Chạy", type="primary", use_container_width=True)
with col2:
    if st.button("🗑️ Xóa lịch sử", use_container_width=False):
        st.session_state.history = []
        st.rerun()

# ── Xử lý query ──────────────────────────────────────────────────────────────
if run_btn and user_question.strip():
    with st.spinner("🤖 Các agents đang xử lý..."):

        # Status indicators
        status_container = st.empty()
        steps = [
            "🔍 Agent 1: Phân tích câu hỏi và lập kế hoạch...",
            "✍️ Agent 2: Sinh câu lệnh SQL...",
            "⚡ Agent 3: Thực thi SQL trên database...",
            "💬 Agent 4: Diễn giải kết quả...",
        ]
        for step in steps:
            status_container.info(step)

        try:
            result = run_query(user_question)
            status_container.success("✅ Hoàn thành!")

            # Lưu vào history
            st.session_state.history.append(result)

        except Exception as e:
            status_container.error(f"❌ Lỗi: {str(e)}")
            st.stop()

# ── Hiển thị kết quả ─────────────────────────────────────────────────────────
if st.session_state.history:
    latest = st.session_state.history[-1]

    st.divider()
    st.subheader("📊 Kết quả")

    # Answer box
    st.success(latest["answer"])

    # Task outputs (collapsible)
    if latest.get("tasks_output"):
        task_labels = ["🗺️ Kế hoạch truy vấn", "📝 SQL đã sinh", "⚡ Kết quả thực thi", "💬 Diễn giải"]
        for i, (label, output) in enumerate(zip(task_labels, latest["tasks_output"])):
            with st.expander(label, expanded=(i == 1)):  # SQL mở mặc định
                st.text(output)

    # Query history
    if len(st.session_state.history) > 1:
        st.divider()
        st.subheader("📜 Lịch sử câu hỏi")
        for i, item in enumerate(reversed(st.session_state.history[:-1]), 1):
            with st.expander(f"#{i}: {item['question']}"):
                st.write(item["answer"])
