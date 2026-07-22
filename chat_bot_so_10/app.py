import os
import json
import base64
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & CUSTOM CSS
# ==================================================
st.set_page_config(
    page_title="Gia sư Hóa học THCS - THCS Phan Chu Trinh", 
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Nunito', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }

    /* Card thông tin ở Sidebar */
    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }

    /* Bong bóng chat HỌC SINH */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
    .stChatMessage:nth-child(odd) {
        background-color: #e0f2fe !important;
        border: 1px solid #bae6fd !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 12px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
    }

    /* Bong bóng chat THẦY GIÁO */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
    .stChatMessage:nth-child(even) {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #0284c7 !important;
        border-radius: 18px 18px 18px 4px !important;
        padding: 14px 20px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.04) !important;
    }

    /* Ô nhập liệu */
    [data-testid="stChatInput"] {
        border-radius: 25px !important;
        border: 2px solid #38bdf8 !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15) !important;
        padding: 4px 8px !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #0284c7 !important;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.25) !important;
    }

    [data-testid="stChatInputSubmitButton"] {
        background-color: #0284c7 !important;
        color: white !important;
        border-radius: 50% !important;
    }
    
    [data-testid="stChatInputSubmitButton"]:hover {
        background-color: #0369a1 !important;
    }

    .stImage img {
        border-radius: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 📂 NẠP CẤU HÌNH VÀ KHỞI TẠO DỮ LIỆU
# ==================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")

def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_value
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

INITIAL_MESSAGE = {"role": "assistant", "content": "Xin chào em! Thầy là Gia sư Hóa học THCS. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"}

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [INITIAL_MESSAGE])

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# 🔑 KHỞI TẠO GEMINI CLIENT
# ==================================================
api_key = os.environ.get("GEMINI_API_KEY")
client = None

if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Lỗi kết nối Gemini API: {e}")
else:
    st.warning("Chưa cấu hình GEMINI_API_KEY trong Secrets.")

SYSTEM_INSTRUCTION = """
Bạn là Gia sư Hóa học THCS dành cho học sinh Trường THCS Phan Chu Trinh (Krông Búk).
- Chỉ giải đáp kiến thức Hóa học THCS (Lớp 8, 9).
- Tên nguyên tố/chất áp dụng danh pháp IUPAC (vd: Oxygen, Hydrogen, Iron, Sulfur...).
- Giảng giải thân thiện, dễ hiểu, đóng vai Thầy giáo xưng "Thầy" gọi "em".
"""

ERROR_MESSAGE_TAG = "[MISSING_DOC_ERROR]"
ERROR_MESSAGE = "Dữ liệu chưa cập nhật câu hỏi này. Thầy đã ghi nhận và sẽ bổ sung sau nhé!"

if client:
    try:
        chat_session = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3
            )
        )
    except Exception as e:
        st.error(f"Lỗi khởi tạo chat session: {e}")

# ==================================================
# 📌 THANH BÊN TRÁI (SIDEBAR)
# ==================================================
with st.sidebar:
    st.title("🧪 Lớp Hóa Học THCS")
    st.caption("Trường THCS Phan Chu Trinh - Krông Búk")
    st.divider()

    st.markdown("""
    <div class="sidebar-card">
        🎯 <b>Gia sư Trực tuyến</b><br>
        Hỗ trợ học sinh ôn tập, giải bài tập & củng cố kiến thức Hóa học lớp 8, 9 theo GDPT 2018 (IUPAC).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 Hướng dẫn:")
    st.markdown("""
    - Nhập câu hỏi bài tập hoặc lý thuyết cần giải đáp.
    - Dùng tên chất theo chuẩn mới (VD: *Oxygen*, *Hydrogen*, *Aluminium*...).
    """)
    
    st.divider()

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = [INITIAL_MESSAGE]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

# ==================================================
# 🏛️ GIAO DIỆN CHÍNH (MAIN DISPLAY)
# ==================================================

# 📍 1. BANNER
banner_loaded = False
for name in ["banner.png", "banner.PNG", "banner.jpg", "banner.jpeg"]:
    banner_path = os.path.join(CURRENT_DIR, name)
    if os.path.exists(banner_path):
        st.image(banner_path, use_container_width=True)
        banner_loaded = True
        break

if not banner_loaded:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 1.5rem; border-radius: 16px; color: white; text-align: center; margin-bottom: 1.5rem;">
        <h2 style="margin:0; font-size: 1.8rem;">🧪 GIA SƯ HOÁ HỌC THCS</h2>
        <p style="margin:5px 0 0 0; opacity: 0.9;">TRƯỜNG THCS PHAN CHU TRINH - KRÔNG BÚK</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 📍 2. KHUNG HỘI THOẠI CHAT
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        avatar_icon = "👨‍🏫" if msg["role"] == "assistant" else "🎒"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

st.markdown("<br>", unsafe_allow_html=True)

# 📍 3. KHU VỰC NHẬP LIỆU BÊN DƯỚI
prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào hôm nay...")

# ==================================================
# 🤖 XỬ LÝ LÔ-GÍC PHẢN HỒI (AI LOGIC)
# ==================================================
if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    
    st.session_state.messages.append({"role": "user", "content": cleaned_prompt})
    save_data(HISTORY_FILE, st.session_state.messages)

    with chat_placeholder:
        with st.chat_message("user", avatar="🎒"):
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant", avatar="👨‍🏫"):
            with st.spinner("Thầy đang suy nghĩ bài làm..."):
                try:
                    message_parts = [types.Part.from_text(text=cleaned_prompt)]
                    response = chat_session.send_message(message_parts)
                    res_text = response.text.strip()
                    
                    if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                        if cleaned_prompt not in st.session_state.missing_questions:
                            st.session_state.missing_questions.append(cleaned_prompt)
                            save_data(STORAGE_FILE, st.session_state.missing_questions)
                        final_res = ERROR_MESSAGE
                    else:
                        final_res = res_text

                    st.markdown(final_res)
                    st.session_state.messages.append({"role": "assistant", "content": final_res})
                    save_data(HISTORY_FILE, st.session_state.messages)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Thầy gặp sự cố kết nối: {e}")
