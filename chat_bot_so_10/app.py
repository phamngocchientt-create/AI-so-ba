import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & CSS BONG BÓNG ZALO NATIVE
# ==================================================
st.set_page_config(
    page_title="Gia sư Hóa học THCS - THCS Phan Chu Trinh", 
    page_icon="🧪",
    layout="wide"
)

# CSS Ép giao diện st.chat_message thành khung bong bóng Zalo
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #f1f5f9;
    }

    /* 💬 PHẦN BONG BÓNG BÊN TRÁI (THẦY GIÁO) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse !important;
    }

    /* Bong bóng tin nhắn Thầy (Trắng, viền xám nhẹ) */
    [data-testid="stChatMessage"]:nth-child(even) [data-testid="stChatMessageContent"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-radius: 4px 20px 20px 20px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04) !important;
        padding: 14px 18px !important;
    }

    /* Bong bóng tin nhắn Học sinh (Màu xanh Zalo) */
    [data-testid="stChatMessage"]:nth-child(odd) [data-testid="stChatMessageContent"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border-radius: 20px 4px 20px 20px !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.22) !important;
        padding: 12px 18px !important;
    }

    /* Đổi màu chữ của học sinh thành màu trắng */
    [data-testid="stChatMessage"]:nth-child(odd) [data-testid="stChatMessageContent"] p {
        color: #ffffff !important;
    }

    /* Tối ưu ô nhập tin nhắn */
    [data-testid="stChatInput"] {
        border-radius: 30px !important;
        border: 2px solid #38bdf8 !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15) !important;
    }

    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 📂 XỬ LÝ DỮ LIỆU
# ==================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")
PASSWORD_KEY = "CLEAR_PASSWORD"

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

HARDCODED_GREETING = "Xin chào em! Thầy là Gia sư Hóa học THCS. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# 📚 RAG & GEMINI API CONFIG
# ==================================================
DOC_FILES = ["tai_lieu_hoa.txt", "giao_an_hoa.txt", "tai_lieu_hoa.pdf"]
knowledge_base_text = ""
has_rag_data = False

for doc_name in DOC_FILES:
    doc_path = os.path.join(CURRENT_DIR, doc_name)
    if os.path.exists(doc_path):
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                knowledge_base_text = f.read().strip()
                if knowledge_base_text:
                    has_rag_data = True
                    break
        except Exception:
            pass

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = None

if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Lỗi kết nối Gemini API: {e}")

BASE_INSTRUCTION = r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Khoa học tự nhiên (phân môn Hóa học 8-9) tại trường THCS Phan Chu Trinh (Krông Búk).
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình GDPT 2018 cấp THCS.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Iron(III) oxide, Sulfate...). TUYỆT ĐỐI KHÔNG dùng tên cũ (Sắt, Nhôm, Đồng).
3. ĐIỀU KIỆN CHUẨN (ĐKC): Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).

# 📐 QUY TẮC LATEX
- Phương trình hóa học viết riêng dòng dùng $$...$$:
  $$2Na + 2H_2O \rightarrow 2NaOH + H_2\uparrow$$
- Công thức nhỏ dùng $...$: $Al_2O_3$, $H_2SO_4$.
"""

ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của Thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"

if has_rag_data:
    SYSTEM_INSTRUCTION = f"{BASE_INSTRUCTION}\nTÀI LIỆU:\n{knowledge_base_text}"
else:
    SYSTEM_INSTRUCTION = BASE_INSTRUCTION

if client:
    try:
        chat_session = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2 if has_rag_data else 0.3
            )
        )
    except Exception as e:
        st.error(f"Lỗi khởi tạo chat session: {e}")

# ==================================================
# 🏛️ GIAO DIỆN CHAT ZALO + KATEX LATEX HOÀN HẢO
# ==================================================

# Sidebar
with st.sidebar:
    st.title("🧪 Lớp Hóa Học THCS")
    st.caption("Trường THCS Phan Chu Trinh - Krông Búk")
    st.divider()

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

# Banner
banner_loaded = False
for name in ["banner.png", "banner.PNG", "banner.jpg", "banner.jpeg", "banner.JPG"]:
    banner_path = os.path.join(CURRENT_DIR, name)
    if os.path.exists(banner_path):
        st.image(banner_path, use_container_width=True)
        banner_loaded = True
        break

if not banner_loaded:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 1.2rem; border-radius: 16px; color: white; text-align: center;">
        <h2 style="margin:0;">🧪 GIA SƯ HOÁ HỌC THCS</h2>
        <p style="margin:0;">TRƯỜNG THCS PHAN CHU TRINH - KRÔNG BÚK</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Hiển thị bong bóng Chat
for msg in st.session_state.messages:
    avatar_icon = "👨‍🏫" if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.markdown(msg["content"])

# Nhập tin nhắn
prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào hôm nay...")

if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()

    st.session_state.messages.append({"role": "user", "content": cleaned_prompt})
    save_data(HISTORY_FILE, st.session_state.messages)

    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(cleaned_prompt)

    with st.chat_message("assistant", avatar="👨‍🏫"):
        with st.spinner("Thầy đang xem bài..."):
            try:
                response = chat_session.send_message([types.Part.from_text(text=cleaned_prompt)])
                res_text = response.text.strip()
                
                st.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})
                save_data(HISTORY_FILE, st.session_state.messages)
                st.rerun()
                
            except Exception as e:
                st.error(f"Sự cố kết nối: {e}")
