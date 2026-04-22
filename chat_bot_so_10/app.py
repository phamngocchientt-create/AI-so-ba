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
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS trường Phan Chu Trinh, em có câu hỏi nào cho thầy không?"

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
st.title("👨‍🔬 Gia sư Hóa học THCS - Phan Chu Trinh")

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ CẤU HÌNH CHAT SESSION (BẢN CƯỜNG HÓA GROUNDING)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # --- ĐỌC TÀI LIỆU TRỰC TIẾP ---
    knowledge_base = ""
    if os.path.exists("files"):
        for filename in os.listdir("files"):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join("files", filename), "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- NGUỒN TRI THỨC ({filename}) ---\n" + f.read()
                except: pass

    # LỆNH ÉP AI TUÂN THỦ DỮ LIỆU FILE (Grounding)
    strict_rule = (r"""
# 🚨 QUY TẮC TỐI THƯỢNG
1. Bạn BẮT BUỘC phải ưu tiên sử dụng thông tin trong phần "KHO TRI THỨC ĐƯỢC NẠP" bên dưới để trả lời.
2. Nếu câu hỏi của học sinh KHÔNG CÓ trong kho tri thức đó, bạn phải từ chối khéo léo bằng mẫu ERROR_MESSAGE và kèm mã [MISSING_DOC].
3. TUYỆT ĐỐI KHÔNG dùng kiến thức nâng cao bên ngoài nếu tài liệu không đề cập.
""")

    # Giữ nguyên Prompt tâm huyết của Thầy
    prompt_engineering = (r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS, hoạt động theo kiến thức chương trình GDPT 2018, lưu ý hãy sử dụng danh pháp quốc tế theo chương trình GDPT 2018. 
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em". 
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm trường Phan Chu Trinh.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING 3 CẤP ĐỘ)
[... Nội dung 3 lựa chọn A, B, C của Thầy ...]

# 🧩 CHIẾN LƯỢC TRUY XUẤT PHÂN TẦNG (XML TAG LOGIC)
[... Các quy tắc thẻ <co_ban>, <huong_dan_giai> của Thầy ...]

# 📐 QUY TẮC HIỂN THỊ & LATEX
[... Các quy tắc bọc $ và $$ của Thầy ...]
    """)

    # Kết hợp: Lệnh ép -> Prompt Thầy -> Tài liệu
    full_instruction = strict_rule + prompt_engineering + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP (DỮ LIỆU GỐC):\n" + knowledge_base

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.0)
        )
        return client, chat, len(knowledge_base)
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 🤖 GIAO DIỆN BÊN TRÁI (SIDEBAR)
# ==================================================
with st.sidebar:
    st.info(f"📊 Thư viện tri thức: {total_chars} ký tự đã được nạp.")
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
# 🤖 XỬ LÝ TIN NHẮN
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
                    st.error(f"Lỗi: {e}")
