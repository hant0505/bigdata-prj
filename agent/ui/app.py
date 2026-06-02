"""
SQL Intelligence - Streamlit UI
Chạy: streamlit run ui/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from main_benchmark_test import run_query
from tools.schema_tool import ExecuteSQLTool

DATABASE_SCHEMA = """
movies            (id, name, year, rank)
actors            (id, first_name, last_name, gender)
directors         (id, first_name, last_name)
movies_genres     (movie_id, genre)
movies_directors  (director_id, movie_id)
roles             (actor_id, movie_id, role)
directors_genres  (director_id, genre, prob)
"""

SAMPLE_QUESTIONS = [
    "Mỗi năm có bao nhiêu bộ phim được phát hành? Chỉ hiển thị những năm có trên 1000 bộ phim.",
    "Top 5 diễn viên tham gia nhiều bộ phim nhất?",
    "Liệt kê các bộ phim thuộc thể loại 'Action' có điểm đánh giá cao nhất.",
    "Đạo diễn nào có nhiều bộ phim nhất trong thập kỷ qua?",
    "What are the top 5 highest-rated movies?",
]

# ── Cấu hình trang ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 IMDb SQL Intelligence Agent",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 IMDb SQL Intelligence Agent")
st.caption("Hỏi về dữ liệu silver parquet (MinIO) bằng tiếng Việt hoặc tiếng Anh — không cần biết SQL")

# ── Chat history ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "selected_history_index" not in st.session_state:
    st.session_state.selected_history_index = None

# ── Sidebar: Chat history ─────────────────────────────────────────────────────
with st.sidebar:
    if st.button("➕ Đoạn chat mới", use_container_width=True):
        st.session_state.history = []
        st.session_state.selected_history_index = None
        st.session_state.pop("input_question", None)
        st.rerun()

    st.divider()
    st.caption("Lịch sử chat")

    if st.session_state.history:
        for idx, item in reversed(list(enumerate(st.session_state.history))):
            question = item.get("question", f"Câu hỏi #{idx + 1}")
            title = question if len(question) <= 70 else f"{question[:67]}..."
            if st.button(title, key=f"history_{idx}", use_container_width=True):
                st.session_state.selected_history_index = idx
                st.rerun()
    else:
        st.caption("Chưa có cuộc trò chuyện nào.")

# ── Database schema ───────────────────────────────────────────────────────────
with st.expander("📋 Xem cấu trúc Database Schema (IMDb)", expanded=False):
    st.code(DATABASE_SCHEMA, language="text")

# ── Input ─────────────────────────────────────────────────────────────────────
default_val = st.session_state.pop("input_question", "")

col1, col2 = st.columns([3, 1])

with col1:
    with st.form("query_form", clear_on_submit=False):
        user_question = st.text_input(
            "💬 Nhập câu hỏi của bạn:",
            value=default_val,
            placeholder="VD: Top 5 diễn viên tham gia nhiều bộ phim nhất?",
        )

        run_btn = st.form_submit_button(
            "🚀 Chạy",
            type="primary",
            use_container_width=True,
        )

with col2:
    st.write("")
    st.write("")
    if st.button("🗑️ Xóa lịch sử", use_container_width=True):
        st.session_state.history = []
        st.session_state.selected_history_index = None
        st.rerun()

# ── Sample questions ──────────────────────────────────────────────────────────
if not st.session_state.history:
    st.markdown("**💡 Câu hỏi mẫu**")
    sample_cols = st.columns(2)
    for idx, question in enumerate(SAMPLE_QUESTIONS):
        with sample_cols[idx % 2]:
            if st.button(question, key=f"sample_{idx}", use_container_width=True):
                st.session_state["input_question"] = question
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
            st.session_state.selected_history_index = len(st.session_state.history) - 1

        except Exception as e:
            status_container.error(f"❌ Lỗi: {str(e)}")
            st.stop()

# ── Hiển thị kết quả ─────────────────────────────────────────────────────────
if st.session_state.history:
    selected_index = st.session_state.selected_history_index
    if selected_index is None or selected_index >= len(st.session_state.history):
        selected_index = len(st.session_state.history) - 1
        st.session_state.selected_history_index = selected_index

    latest = st.session_state.history[selected_index]

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