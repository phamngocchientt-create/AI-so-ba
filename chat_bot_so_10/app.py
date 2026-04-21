import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 
import time

# ==================================================
# 📌 CẤU HÌNH HỆ THỐNG
# ==================================================
# Đảm bảo 2 file này có đuôi .txt và nằm trong thư mục files/
LIST_FILES_LOCAL = ['files/qtkb5el1kzuo.txt', 'files/99c3izk5v98v.txt'] 
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

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
# KHỞI TẠO ỨNG DỤNG STREAMLIT
# ==================================================
st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

with st.sidebar:
    st.success(f"✅ Đã kết nối tri thức từ thư viện.")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung")
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            if st.form_submit_button("Xóa Toàn bộ"):
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    st.session_state.missing_questions = []
                    save_data(STORAGE_FILE, [])
                    st.success("✅ Đã xóa!")
                    st.rerun()
                else: st.error("❌ Sai mật khẩu.")
    else:
        st.write("Không có câu hỏi nào cần bổ sung.")

# ==================================================
# ⚙️ CẤU HÌNH CHAT SESSION (ĐÃ FIX LỖI NAMEERROR DẤU NGOẶC)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None 

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # Đọc nội dung file văn bản
    knowledge_text = ""
    for file_path in LIST_FILES_LOCAL:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                knowledge_text += f"\n--- DỮ LIỆU TỪ {file_path} ---\n"
                knowledge_text += f.read() + "\n"

    # LƯU Ý: Các công thức LaTeX có ngoặc nhọn phải viết thành {{ }} để tránh lỗi NameError
    sys_instruct = f"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS (Trường Phan Chu Trinh).
- Phong cách: "Thầy" - "Em".
- Mục tiêu: Dẫn dắt, khích lệ học sinh.

# 📚 KHO TRI THỨC GỐC (GROUNDING DATA):
{knowledge_text}

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
1. CÂU HỎI BÀI TẬP: Đưa ra 3 lựa chọn A, B, C.
2. DẪN DẮT: Dùng thẻ <huong_dan_giai>, tuyệt đối không làm hộ phép tính.

# 📐 QUY TẮC HIỂN THỊ & LATEX (ĐÃ FIX)
- Công thức hóa học: Ví dụ $H_2SO_4$.
- Công thức tính toán: $n = \\frac{{m}}{{M}}$ (Lưu ý: dùng hai dấu ngoặc nhọn).
- PTHH: Đặt trong $$...$$ và xuống dòng trống.
  Ví dụ:
  $$2H_2 + O_2 \\xrightarrow{{t^o}} 2H_2O$$

# 📚 GIỚI HẠN
Chỉ trả lời trong phạm vi Hóa học 8-9. Nếu thiếu dùng mã [MISSING_DOC].
"""

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.2)
        )
        return client, chat
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🤖 GIAO DIỆN VÀ XỬ LÝ TIN NHẮN
# ==================================================
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="fixed_bottom_uploader")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

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
        with st.chat_message("user"):
            if uploaded_file: st.image(uploaded_file, width=300)
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thầy đang xem bài..."):
                try:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
                    
                    response = None
                    for attempt in range(3):
                        try:
                            response = chat_session.send_message(message_parts)
                            break
                        except Exception as e:
                            if "429" in str(e) and attempt < 2:
                                time.sleep(5)
                                continue
                            else: raise e

                    res_text = response.text.strip()
                    
                    if ERROR_MESSAGE_TAG in res_text:
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
                    st.error(f"Lỗi: {e}")
