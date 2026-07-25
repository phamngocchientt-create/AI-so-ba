import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & CSS GIAO DIỆN CHAT ZALO
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

    /* Tối ưu khung chat message chuẩn màu Zalo */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 0.5rem 0 !important;
    }

    /* Khung nhập liệu */
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
# 📂 XỬ LÝ DỮ LIỆU & QUẢN LÝ TỆP
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
# 🔑 SYSTEM INSTRUCTION
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
3. ĐIỀU KIỆN CHUẨN (ĐKC): Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).

# 🎓 CHIẾN LƯỢC XỬ LÝ SƯ PHẠM (QUAN TRỌNG)
1. CÂU HỎI LÝ THUYẾT: Trả lời cô đọng, đi thẳng vào bản chất cơ bản trước. Không mở rộng quá sâu trừ khi học sinh yêu cầu.
2. CÂU HỎI BÀI TẬP: Tuyệt đối không giải ngay trong lần đầu. Đưa ra 3 lựa chọn:
   * **Lựa chọn A:** Thầy hướng dẫn em tư duy từng bước một (Khuyên dùng).
   * **Lựa chọn B:** Thầy đưa ra "sơ đồ các bước làm" để em tự thực hành.
   * **Lựa chọn C:** Thầy gửi luôn bài giải chi tiết để em tham khảo và đối chiếu.

# 📐 QUY TẮC HIỂN THỊ CÔNG THỨC & LATEX
1. KHOẢNG TRẮNG: Sử dụng "Dòng trống" (Double Enter) giữa các đoạn văn, giữa đề mục và nội dung.
2. ĐỀ MỤC: Các mục lớn (I, II, III...), mục nhỏ (a, b, c...) dùng `###` hoặc `**in đậm**` trên một dòng riêng.
3. PHƯƠNG TRÌNH HÓA HỌC (PTHH):
   - Phải bọc trong `$$...$$` và nằm trên dòng riêng biệt.
   - Ví dụ:
   $$2Na + 2H_2O \rightarrow 2NaOH + H_2\uparrow$$
   $$Mg + H_2O_{(hơi)} \xrightarrow{t^o} MgO + H_2\uparrow$$
4. CÔNG THỨC & TÊN CHẤT NẰM TRONG CÂU:
   - Các công thức ngắn bọc trong `$ ... $`.
   - Ví dụ: $Al_2O_3$, $n = \frac{m}{M}$.
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
# 🏛️ GIAO DIỆN CHÍNH (NATIVE MARKDOWN - LATEX CHUẨN 100%)
# ==================================================

# 📍 BANNER
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

# 📍 CỦNG CỐ CÔNG THỨC LATEX BẰNG REGEX TRƯỚC KHU VỰC HIỂN THỊ
def format_latex_display(text):
    if not text:
        return ""
    # Đảm bảo các phương trình $$ luôn đứng riêng dòng trống để Streamlit Markdown render đẹp nhất
    text = re.sub(r'([^\n\$])(\$\$)', r'\1\n\n\2', text)
    text = re.sub(r'(\$\$)([^\n\$])', r'\1\n\n\2', text)
    return text

# 📍 KHUNG HỘI THOẠI CHAT CHÍNH
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        avatar_icon = "👨‍🏫" if msg["role"] == "assistant" else "🧑‍🎓"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(format_latex_display(msg["content"]))

st.markdown("<br>", unsafe_allow_html=True)

# 📍 KHU VỰC NHẬP LIỆU BÊN DƯỚI
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
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant", avatar="👨‍🏫"):
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

                    st.markdown(format_latex_display(final_res))
                    st.session_state.messages.append({"role": "assistant", "content": final_res})
                    save_data(HISTORY_FILE, st.session_state.messages)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Thầy gặp sự cố kết nối: {e}")
