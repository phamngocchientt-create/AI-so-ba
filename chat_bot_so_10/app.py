import streamlit as st
from google import genai
from google.genai import types
import os
import json

# ==================================================
# 📌 CẤU HÌNH HỆ THỐNG & FILE
# ==================================================
LIST_FILES = ['files/o4a2cyiaer8u', 'files/ekowcvd537b9']
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json"
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào em! Thầy là Gia sư Hóa học THCS. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"

# --- HÀM XỬ LÝ JSON ---
def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return default_value
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# ==================================================
# 🎨 CẤU HÌNH TRANG & CUSTOM CSS (PHÂN BIỆT BONG BÓNG CHAT)
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

    /* Tùy biến Sidebar Card */
    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }

    /* ==================================================
       🔥 PHÂN BIỆT RÕ RÀNG BONG BÓNG CHAT THẦY & TRÒ
       ================================================== */
    
    /* 1. BONG BÓNG CHAT HỌC SINH (USER) - MÀU XÁM XANH */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat avatar user"]),
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background-color: #e2e8f0 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 18px 18px 4px 18px !important;
        margin-left: 3rem !important;
        margin-bottom: 1rem !important;
    }

    /* 2. BONG BÓNG CHAT THẦY GIÁO (ASSISTANT) - MÀU XANH LÁ PASTEL */
    div[data-testid="stChatMessage"]:has(div[aria-label="Chat avatar assistant"]),
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #ecfdf5 !important;
        border: 1.5px solid #a7f3d0 !important;
        border-radius: 18px 18px 18px 4px !important;
        margin-right: 3rem !important;
        margin-bottom: 1rem !important;
    }

    /* Làm nổi bật Avatar */
    div[data-testid="stChatMessageAvatarUser"], 
    div[data-testid="stChatMessageAvatarAssistant"] {
        background-color: transparent !important;
    }

    /* Bo góc ô upload file */
    div[data-testid="stFileUploader"] {
        background-color: #ffffff;
        border: 1.5px dashed #0284c7;
        border-radius: 12px;
        padding: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ CẤU HÌNH CHAT SESSION & XỬ LÝ LỖI FILE 403
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    client = genai.Client(api_key=api_key)
    
    sys_instruct = (r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Hóa học THCS (lớp 8, lớp 9) tại trường THCS Phan Chu Trinh.
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình Hóa học THCS. Tuyệt đối không đưa kiến thức THPT/Đại học vào bài giảng.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Iron(III) oxide, Sulfate...). TUYỆT ĐỐI KHÔNG dùng tên cũ (Sắt, Nhôm, Đồng).
3. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
4. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ khi HS yêu cầu ĐÍCH DANH.
5. ĐƠN VỊ: Khối lượng nguyên tử dùng "amu". Áp suất dùng "bar".

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
1. CÂU HỎI LÝ THUYẾT: Trả lời trực tiếp, rõ ràng.
2. CÂU HỎI BÀI TẬP (TÍNH TOÁN/LÝ THUYẾT): Tuyệt đối không giải ngay. Hãy chào đón và đưa ra 3 lựa chọn:
   * Lựa chọn A: Thầy hướng dẫn em tư duy từng bước (Khuyên dùng).
   * Lựa chọn B: Thầy đưa ra "bản đồ" (phác thảo các bước giải) để em tự đi.
   * Lựa chọn C: Thầy đưa bài giải chi tiết để em đối chiếu.
   - Nếu em chọn C hoặc yêu cầu khẩn thiết, đưa bài giải đầy đủ lời giải, công thức và phép tính.

# 📐 QUY TẮC HIỂN THỊ
1. KHOẢNG TRẮNG: Sử dụng "Dòng trống" (Double Enter) giữa các đoạn văn.
2. ĐỀ MỤC: Các mục lớn phải **IN ĐẬM** và đứng riêng một dòng.
3. PHƯƠNG TRÌNH HÓA HỌC: Phải bọc trong $$...$$ và nằm trên dòng riêng biệt.
4. CÔNG THỨC & LATEX: Công thức bọc trong $...$ hoặc $$...$$.
    """)

    try:
        chat = client.chats.create(
            model="gemini-2.5-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.2)
        )
        
        # Bỏ qua file lỗi 403 để ứng dụng không bị hiện thông báo đỏ
        list_parts = []
        valid_files_count = 0
        for file_id in LIST_FILES:
            try:
                uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_id}"
                list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain"))
                valid_files_count += 1
            except Exception:
                continue
        
        if list_parts:
            list_parts.append(types.Part.from_text(text="Nạp tài liệu. Chỉ trả lời dựa trên đây. Nếu thiếu dùng mã [MISSING_DOC]."))
            chat.send_message(list_parts)
            
        return client, chat, valid_files_count
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo hệ thống: {e}")
        return None, None, 0

client, chat_session, active_files_count = setup_chat_session() 

# ==================================================
# 📌 SIDEBAR (THANH QUẢN LÝ BÊN TRÁI)
# ==================================================
with st.sidebar:
    st.markdown("### 🏫 Góc Quản Lý Giáo Viên")
    
    st.markdown(f"""
    <div class="sidebar-card">
        <b style="color: #0284c7;">🧪 Thư viện Hóa học THCS</b><br>
        <small>Đã kết nối an toàn: <b>{active_files_count} tài liệu</b></small>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Xóa lịch sử Trò chuyện", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

    st.markdown("---")
    st.markdown("### 📝 Sổ Tay Bổ Sung Knowledge")
    
    if st.session_state.missing_questions:
        st.caption("Các câu hỏi học sinh hỏi nhưng chưa có trong tài liệu:")
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
        
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu xóa", type="password")
            if st.form_submit_button("Xóa danh sách", use_container_width=True):
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    st.session_state.missing_questions = []
                    save_data(STORAGE_FILE, [])
                    st.success("✅ Đã xóa!")
                    st.rerun()
                else: st.error("❌ Mật khẩu chưa đúng.")
    else:
        st.info("Chưa có câu hỏi thiếu.")

# ==================================================
# 🏛️ GIAO DIỆN CHÍNH (MAIN DISPLAY)
# ==================================================

# 📍 1. HIỂN THỊ BANNER (TỰ ĐỘNG LẤY ANH BANNER)
if os.path.exists("banner.png"):
    st.image("banner.png", use_container_width=True)
elif os.path.exists("banner.jpg"):
    st.image("banner.jpg", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# 📍 2. KHUNG HỘI THOẠI CHAT
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        avatar_icon = "👨‍🏫" if msg["role"] == "assistant" else "🎒"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

# 📍 3. KHU VỰC NHẬP LIỆU & GỬI ẢNH GỌN GÀNG BÊN DƯỚI
st.markdown("<br>", unsafe_allow_html=True)

# Gom ô upload và ô chat chung hàng cho gọn gàng
col_file, col_input = st.columns([1, 5])

with col_file:
    uploaded_file = st.file_uploader(
        "📎 Gửi ảnh bài tập", 
        type=["jpg", "jpeg", "png"], 
        key="compact_uploader",
        help="Đính kèm ảnh bài tập Hóa học"
    )

with col_input:
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
        user_msg_content = f"📝 *(Kèm ảnh đề bài)*\n\n{cleaned_prompt}"
    
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)

    with chat_placeholder:
        with st.chat_message("user", avatar="🎒"):
            if uploaded_file: st.image(uploaded_file, width=280)
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant", avatar="👨‍🏫"):
            with st.spinner("Thầy đang suy nghĩ bài làm..."):
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
                    st.error(f"Thầy gặp sự cố kết nối: {e}")
