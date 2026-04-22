import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 
import time

# ==================================================
# 📌 1. CẤU HÌNH HỆ THỐNG
# ==================================================
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG}"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào em, thầy là Gia sư Hoá học THCS trường Phan Chu Trinh. Thầy đã sẵn sàng đồng hành cùng em rồi đây!"

# --- HÀM XỬ LÝ DỮ LIỆU ---
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
# 📌 2. KHỞI TẠO GIAO DIỆN STREAMLIT
# ==================================================
st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Trường Phan Chu Trinh")

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# 📌 3. CẤU HÌNH CHAT SESSION (BẢN SƯ PHẠM ĐẸP MẮT)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # --- NẠP TÀI LIỆU TỪ THƯ MỤC 'files' ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(current_dir, "files")
    knowledge_base = ""
    if os.path.exists(files_dir):
        for filename in os.listdir(files_dir):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join(files_dir, filename), "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- DỮ LIỆU FILE {filename} ---\n" + f.read()
                except: pass

    # --- NỘI DUNG PROMPT ENGINEERING (ĐÃ TỐI ƯU HIỂN THỊ) ---
    sys_instruct = (r"""
# 🚨 QUY TẮC HIỂN THỊ (QUAN TRỌNG NHẤT)
1. TUYỆT ĐỐI KHÔNG trích dẫn nguyên văn các thẻ như <co_ban>, <huong_dan_giai> ra màn hình. Đó chỉ là dữ liệu nội bộ.
2. Hãy đóng vai một người Thầy giảng bài: Diễn đạt lại kiến thức bằng ngôn ngữ tự nhiên, đẹp mắt, dễ hiểu.
3. Sử dụng Markdown (đậm, nghiêng, bảng, danh sách) để trình bày lời giải thật rõ ràng.
4. Ưu tiên sử dụng kiến thức trong "KHO TRI THỨC ĐƯỢC NẠP" bên dưới. Nếu không có, hãy báo [MISSING_DOC].

# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" môn Hóa học THCS trường Phan Chu Trinh. Xưng "Thầy", gọi "Em".
Phong cách: Tâm huyết, khích lệ, đúng chuẩn sư phạm.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
- Bước 1: Chẩn đoán & đưa ra 3 lựa chọn A (Tư duy), B (Bản đồ giải), C (Đáp án chi tiết).
- Bước 2: Dẫn dắt bằng câu hỏi gợi mở, tuyệt đối không làm hộ phép tính.

# 📐 QUY TẮC LATEX & TRÌNH BÀY
- Công thức hóa học: Phải bọc trong $...$ (Ví dụ: $H_2SO_4$).
- Công thức tính toán: Phải bọc trong $...$ (Ví dụ: $n = \frac{m}{M}$).
- PTHH: Phải nằm trên một dòng riêng, bọc trong $$...$$ và cách dòng trống với văn bản.
- Danh pháp: IUPAC (Oxide, Aluminium...). Điều kiện chuẩn: 24,79 L.
    """)

    full_instruction = sys_instruct + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP (DỮ LIỆU GỐC):\n" + knowledge_base

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.0)
        )
        return client, chat, len(knowledge_base)
    except:
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 📌 4. SIDEBAR & KHUNG CHAT
# ==================================================
with st.sidebar:
    if total_chars > 0:
        st.success(f"✅ Đã nạp {total_chars} ký tự tri thức.")
    else:
        st.error("❌ 0 ký tự: Thầy hãy kiểm tra lại file .txt trong thư mục 'files'")

    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

# Hiển thị lịch sử Chat
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
# Đảm bảo khung chat luôn hiện ở cuối
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"])
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 📌 5. XỬ LÝ LOGIC
# ==================================================
if prompt:
    if client is None:
        st.error("⚠️ Không thể kết nối AI. Thầy kiểm tra lại GEMINI_API_KEY nhé!")
    else:
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
                        
                        if ERROR_MESSAGE_TAG in res_text or "[MISSING_DOC]" in res_text:
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
