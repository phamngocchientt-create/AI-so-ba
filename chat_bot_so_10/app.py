import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 
import time

# ==================================================
# 📌 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN
# ==================================================
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG}"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS trường Phan Chu Trinh, em có câu hỏi nào cho thầy không?"

# --- HÀM XỬ LÝ DỮ LIỆU (Lưu lịch sử & Câu hỏi thiếu) ---
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
# 📌 3. CẤU HÌNH CHAT SESSION (FIX LỖI 0 KÝ TỰ & 429)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    # Dùng v1beta để hỗ trợ ổn định nhất cho Gemini 2.0
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # --- TỰ ĐỘNG TÌM FILE TRONG THƯ MỤC 'files' ---
    # Lệnh này giúp lấy đường dẫn tuyệt đối, tránh lỗi 0 ký tự trên Cloud
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(current_dir, "files")
    
    knowledge_base = ""
    if os.path.exists(files_dir):
        for filename in os.listdir(files_dir):
            if filename.endswith(".txt"):
                try:
                    file_path = os.path.join(files_dir, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- DỮ LIỆU TỪ FILE {filename} ---\n" + f.read()
                except: pass

    # LỆNH ÉP AI SỬ DỤNG TÀI LIỆU (Strict Grounding)
    strict_rule = (r"""
# 🚨 QUY TẮC TỐI THƯỢNG (BẮT BUỘC)
1. Bạn CHỈ ĐƯỢC PHÉP trả lời dựa trên "KHO TRI THỨC ĐƯỢC NẠP" bên dưới.
2. TUYỆT ĐỐI KHÔNG dùng kiến thức nền bên ngoài nếu tài liệu không đề cập.
3. Nếu không có thông tin trong kho tri thức, hãy báo [MISSING_DOC].
4. KHÔNG tự ý giải bài toán nếu không có công thức hoặc mẫu trong tài liệu.
""")

    # Prompt Engineering tâm huyết của Thầy
    prompt_engineering = (r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS (lớp 8, 9) trường Phan Chu Trinh.
- Xưng "Thầy", gọi "Em". Ngôn ngữ khích lệ, đúng chuẩn sư phạm.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
Khi HS hỏi bài tập, đưa ra 3 lựa chọn:
- Lựa chọn A: Hướng dẫn tư duy từng bước.
- Lựa chọn B: Đưa ra bản đồ giải bài.
- Lựa chọn C: Đưa bài giải chi tiết (Chỉ khi HS thực sự bí).

# 🧩 QUY TẮC THẺ XML
- Sử dụng <co_ban> cho định nghĩa.
- Sử dụng <huong_dan_giai> cho bài tập.
- Chỉ đưa <bai_giai_chi_tiet> khi HS chọn C.

# 📐 QUY TẮC HIỂN THỊ LATEX
- Công thức hóa học bọc trong $...$ (Ví dụ: $H_2SO_4$).
- Phép tính bọc trong $...$ (Ví dụ: $n = \frac{m}{M}$).
- PTHH bọc trong $$...$$ và nằm trên dòng riêng.
""")

    # Kết hợp: Quy tắc nghiêm ngặt + Prompt Sư phạm + Nội dung file
    full_instruction = strict_rule + prompt_engineering + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP:\n" + knowledge_base

    try:
        # Khởi tạo chat với temperature=0.0 để AI không "tự ý sáng tạo" ngoài file
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.0)
        )
        return client, chat, len(knowledge_base)
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 📌 4. SIDEBAR (THANH QUẢN LÝ BÊN TRÁI)
# ==================================================
with st.sidebar:
    if total_chars > 0:
        st.success(f"✅ Đã nạp {total_chars} ký tự tri thức từ thư mục 'files'.")
    else:
        st.error("❌ 0 ký tự: Thầy hãy kiểm tra lại thư mục 'files' trên GitHub nhé!")

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
