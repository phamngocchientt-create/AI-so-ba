import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & STYLES (ZALO CHUẨN + MATHTYPE NATIVE)
# ==================================================
st.set_page_config(
    page_title="Gia sư Hóa học THCS - THCS Phan Chu Trinh", 
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #f1f5f9;
    }

    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }

    /* 💬 ĐỊNH DẠNG AVATAR VÀ BONG BÓNG CHAT STREAMLIT NATIVE */
    
    /* Bo tròn Avatar */
    [data-testid="stChatMessage"] img, 
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
        border-radius: 50% !important;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12) !important;
        border: 2px solid #ffffff !important;
        object-fit: cover !important;
    }

    /* 🎒 CHAT HỌC SINH (BÊN PHẢI - NỀN XANH ZALO) */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        flex-direction: row-reverse !important;
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border-radius: 20px 20px 4px 20px !important;
        padding: 12px 18px !important;
        margin-left: auto !important;
        margin-bottom: 14px !important;
        max-width: 80% !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p {
        color: #ffffff !important;
        font-weight: 500;
    }

    /* 👨‍🏫 CHAT THẦY GIÁO (BÊN TRÁI - NỀN TRẮNG TINH TẾ) */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #0284c7 !important;
        border-radius: 20px 20px 20px 4px !important;
        padding: 16px 20px !important;
        margin-right: auto !important;
        margin-bottom: 14px !important;
        max-width: 85% !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) p {
        color: #0f172a !important;
        line-height: 1.6 !important;
    }

    /* ⌨️ KHUNG NHẬP LIỆU */
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
        background-color: #0284c7 !important;
        color: white !important;
        border-radius: 50% !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 📂 NẠP CẤU HÌNH VÀ TÌM AVATAR
# ==================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")
PASSWORD_KEY = "CLEAR_PASSWORD"

def get_avatar_path(base_name, default_emoji):
    for ext in [".PNG", ".png", ".jpg", ".jpeg", ".JPG", ".JPEG"]:
        path = os.path.join(CURRENT_DIR, f"{base_name}{ext}")
        if os.path.exists(path):
            return path
    return default_emoji

AVATAR_TEACHER = get_avatar_path("teacher_avatar", "👨‍🔬")
AVATAR_STUDENT = get_avatar_path("student_avatar", "🙋‍♂️")

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

HARDCODED_GREETING = "Xin chào em! Thầy là Gia sư Hóa học THCS trường THCS Phan Chu Trinh. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# 📚 ĐỌC TÀI LIỆU DỰ PHÒNG (RAG + FALLBACK)
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
# 🔑 SYSTEM INSTRUCTION CHUẨN GDPT 2018 & LATEX
# ==================================================
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
3. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là 24,79 L/mol (tại 25°C, 1 bar).

# 📐 QUY TẮC HIỂN THỊ CÔNG THỨC LATEX & MATHTYPE (CỰC KỲ QUAN TRỌNG)
1. PHƯƠNG TRÌNH HÓA HỌC (PTHH):
   - Mọi phương trình hóa học BẮT BỘC kẹp trong dấu $$...$$ và nằm riêng trên một dòng độc lập.
   - Ví dụ: 
   $$2Al + 3H_2SO_4 \rightarrow Al_2(SO_4)_3 + 3H_2\uparrow$$
   $$2Ag + 2H_2SO_4 \xrightarrow{t^o} Ag_2SO_4 + SO_2\uparrow + 2H_2O$$
2. CÔNG THỨC TOÁN HỌC & TÍNH TOÁN:
   - Các công thức tính toán ngắn, phân số kẹp trong dấu $...$ (cùng dòng) hoặc $$...$$ (riêng dòng).
   - Ví dụ: $n_{Fe} = \frac{m}{M} = \frac{5,6}{56} = 0,1\text{ mol}$.
   - Dùng \uparrow cho khí bay lên, \downarrow cho chất kết tủa.
"""

ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của Thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"

if has_rag_data:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
    
DƯỚI ĐÂY LÀ BỘ TÀI LIỆU GIÁO ÁN GỐC ĐƯỢC CẤP:
---
{knowledge_base_text}
---

QUY TẮC BẮT BỘC KHI CÓ TÀI LIỆU:
1. Bạn CHỈ ĐƯỢC PHẾP trả lời câu hỏi dựa trên nội dung có trong BỘ TÀI LIỆU GIÁO ÁN GỐC ở trên.
2. Nếu câu hỏi của học sinh KHÔNG nằm trong bộ tài liệu trên, bạn BẮT BUỘC trả về duy nhất mã: {ERROR_MESSAGE_TAG}
"""
else:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
- Sử dụng tri thức Hóa học THCS chuẩn GDPT 2018 để trả lời cho học sinh.
- Nếu gặp câu hỏi hoàn toàn không liên quan đến Hóa học THCS, trả về chuỗi {ERROR_MESSAGE_TAG}
"""

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

    st.divider()
    st.header("📝 Câu hỏi Cần Bổ Sung")
    
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions, 1):
            st.markdown(f"**{i}.** {q}")
        
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            if st.form_submit_button("Xóa Toàn bộ"):
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    st.session_state.missing_questions = []
                    save_data(STORAGE_FILE, [])
                    st.success("✅ Đã xóa!")
                    st.rerun()
                else: 
                    st.error("❌ Sai mật khẩu.")
    else:
        st.write("Không có câu hỏi nào cần bổ sung.")

    st.divider()

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
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

# 📍 2. KHUNG HỘI THOẠI CHAT (SỬ DỤNG STREAMLIT NATIVE ĐỂ RENDER LATEX NÉT CĂNG)
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        avatar = AVATAR_TEACHER if msg["role"] == "assistant" else AVATAR_STUDENT
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

st.markdown("<br>", unsafe_allow_html=True)

# 📍 3. KHU VỰC NHẬP LIỆU BÊN DƯỚI (HỖ TRỢ TẢI ẢNH ĐỀ BÀI)
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="fixed_bottom_uploader")
prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào hôm nay...")

# ==================================================
# 🤖 XỬ LÝ LÔ-GÍC PHẢN HỒI (AI LOGIC)
# ==================================================
if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    message_parts = []
    
    user_msg_content = cleaned_prompt
    if uploaded_file:
        image_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type)
        message_parts.append(image_part)
        user_msg_content = f"📝 (Kèm ảnh) {cleaned_prompt}"

    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)

    with chat_placeholder:
        with st.chat_message("user", avatar=AVATAR_STUDENT):
            if uploaded_file: st.image(uploaded_file, width=300)
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant", avatar=AVATAR_TEACHER):
            with st.spinner("Thầy đang xem bài..."):
                try:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
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
                    st.error(f"Lỗi kết nối: {e}")
