import os
import json
import base64
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & CUSTOM CSS (BONG BÓNG ZALO CHUẨN 100%)
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
        background-color: #eef2f6;
    }

    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }

    /* -------------------------------------------------- */
    /* 💬 GIAO DIỆN BONG BÓNG CHAT KIỂU ZALO THỰC THỤ */
    /* -------------------------------------------------- */
    
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 20px;
    }

    /* BÊN TRÁI: THẦY GIÁO TRẢ LỜI */
    .chat-row-left {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 12px;
        max-width: 80%;
        margin-right: auto;
    }

    .chat-bubble-left {
        background-color: #ffffff;
        color: #1e293b;
        padding: 12px 18px;
        border-radius: 4px 18px 18px 18px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #e2e8f0;
        font-size: 15px;
        line-height: 1.5;
    }

    /* BÊN PHẢI: HỌC SINH NHẮN */
    .chat-row-right {
        display: flex;
        flex-direction: row-reverse;
        align-items: flex-start;
        gap: 12px;
        max-width: 80%;
        margin-left: auto;
    }

    .chat-bubble-right {
        background-color: #0084ff; /* Màu xanh Zalo / Messenger chuẩn */
        color: #ffffff;
        padding: 12px 18px;
        border-radius: 18px 4px 18px 18px;
        box-shadow: 0 2px 8px rgba(0, 132, 255, 0.25);
        font-size: 15px;
        line-height: 1.5;
        font-weight: 500;
    }

    /* Định dạng Avatar tròn đẹp */
    .avatar-img {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        border: 2px solid #ffffff;
        flex-shrink: 0;
    }

    /* ⌨️ KHUNG NHẬP LIỆU NHẮN TIN */
    [data-testid="stChatInput"] {
        border-radius: 30px !important;
        border: 2px solid #38bdf8 !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15) !important;
        padding: 4px 8px !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #0284c7 !important;
    }

    [data-testid="stChatInputSubmitButton"] {
        background-color: #0084ff !important;
        color: white !important;
        border-radius: 50% !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 📂 HÀM CHUYỂN ẢNH SANG BASE64 ĐỂ HIỂN THỊ HTML MƯỢT MA
# ==================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")

def get_image_base64(base_name):
    for ext in [".PNG", ".png", ".jpg", ".jpeg", ".JPG", ".JPEG"]:
        path = os.path.join(CURRENT_DIR, f"{base_name}{ext}")
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
                ext_type = "png" if "png" in ext.lower() else "jpeg"
                return f"data:image/{ext_type};base64,{encoded}"
    return None

TEACHER_B64 = get_image_base64("teacher_avatar")
STUDENT_B64 = get_image_base64("student_avatar")

# Emoji dự phòng nếu thiếu file
DEFAULT_TEACHER_AVATAR = "https://api.dicebear.com/7.x/bottts/svg?seed=Teacher"
DEFAULT_STUDENT_AVATAR = "https://api.dicebear.com/7.x/avataaars/svg?seed=Student"

AVATAR_TEACHER_SRC = TEACHER_B64 if TEACHER_B64 else DEFAULT_TEACHER_AVATAR
AVATAR_STUDENT_SRC = STUDENT_B64 if STUDENT_B64 else DEFAULT_STUDENT_AVATAR

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
# 📚 ĐỌC FILE TÀI LIỆU RAG DỰ PHÒNG (KÈM FALLBACK)
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

# ==================================================
# 🔑 KHỞI TẠO GEMINI CLIENT & TẠO PROMPT ĐỘNG
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

BASE_INSTRUCTION = """
Bạn là Gia sư Hóa học THCS dành cho học sinh Trường THCS Phan Chu Trinh (Krông Búk).
- Chỉ giải đáp kiến thức Hóa học THCS (Lớp 8, 9).
- Tên nguyên tố/chất áp dụng danh pháp IUPAC (vd: Oxygen, Hydrogen, Iron, Sulfur...).
- Giảng giải thân thiện, dễ hiểu, đóng vai Thầy giáo xưng "Thầy" gọi "em".
"""

ERROR_MESSAGE_TAG = "[MISSING_DOC_ERROR]"
ERROR_MESSAGE = "Dữ liệu chưa cập nhật câu hỏi này. Thầy đã ghi nhận và sẽ bổ sung sau nhé!"

if has_rag_data:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
    
DƯỚI ĐÂY LÀ BỘ TÀI LIỆU GIÁO ÁN GỐC ĐƯỢC CẤP:
---
{knowledge_base_text}
---

QUY TẮC BẮT BỘC KHI CÓ TÀI LIỆU:
1. Bạn CHỈ ĐƯỢC PHÉP trả lời câu hỏi dựa trên nội dung có trong BỘ TÀI LIỆU GIÁO ÁN GỐC ở trên.
2. Nếu câu hỏi của học sinh KHÔNG nằm trong bộ tài liệu trên, bạn BẮT BUỘC trả về duy nhất mã: {ERROR_MESSAGE_TAG}
"""
else:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
- Sử dụng tri thức Hóa học THCS chuẩn để trả lời cho học sinh.
- Nếu gặp câu hỏi hoàn toàn không liên quan đến Hóa học THCS, trả về chuỗi {ERROR_MESSAGE_TAG}
"""

if client:
    try:
        chat_session = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2 if has_rag_data else 0.4
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

    if has_rag_data:
        st.success("📚 **Đang dùng:** Tài liệu Giáo án riêng (RAG Mode)")
    else:
        st.warning("⚡ **Đang dùng:** Tri thức mở Gemini 2.5 (Fallback Mode)")

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

    with st.expander("📌 Câu hỏi chưa có dữ liệu", expanded=False):
        if st.session_state.missing_questions:
            st.write(f"Hiện có **{len(st.session_state.missing_questions)}** câu hỏi cần bổ sung:")
            for idx, q in enumerate(st.session_state.missing_questions, 1):
                st.markdown(f"**{idx}.** {q}")
            
            if st.button("🗑️ Xóa danh sách câu hỏi", key="clear_missing"):
                st.session_state.missing_questions = []
                save_data(STORAGE_FILE, st.session_state.missing_questions)
                st.success("Đã xóa danh sách!")
                st.rerun()
        else:
            st.info("Chưa có câu hỏi nào bị thiếu dữ liệu!")

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
for name in ["banner.png", "banner.PNG", "banner.jpg", "banner.jpeg", "banner.JPG"]:
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

# 📍 2. KHUNG HỘI THOẠI CHAT CHUẨN ĐỊNH DẠNG ZALO
chat_placeholder = st.container()

def render_chat_html(role, content):
    content_formatted = content.replace("\n", "<br>")
    if role == "assistant":
        return f"""
        <div class="chat-row-left">
            <img src="{AVATAR_TEACHER_SRC}" class="avatar-img" />
            <div class="chat-bubble-left">{content_formatted}</div>
        </div>
        """
    else:
        return f"""
        <div class="chat-row-right">
            <img src="{AVATAR_STUDENT_SRC}" class="avatar-img" />
            <div class="chat-bubble-right">{content_formatted}</div>
        </div>
        """

with chat_placeholder:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        st.markdown(render_chat_html(msg["role"], msg["content"]), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown(render_chat_html("user", cleaned_prompt), unsafe_allow_html=True)

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

                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_data(HISTORY_FILE, st.session_state.messages)
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Thầy gặp sự cố kết nối: {e}")
