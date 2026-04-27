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
st.title("👨‍🔬 Gia sư Hóa học THCS - Phan Chu Trinh")

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# 📌 3. CẤU HÌNH CHAT SESSION (FIX LỖI 400 & 429)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    # BẮT BUỘC dùng v1beta để không bị lỗi 400 "Unknown name systemInstruction"
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(current_dir, "files")
    
    knowledge_base = ""
    if os.path.exists(files_dir):
        for filename in os.listdir(files_dir):
            if filename.endswith(".txt"):
                try:
                    file_path = os.path.join(files_dir, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- NGUỒN ({filename}) ---\n" + f.read()
                except: pass

    # PROMPT ENGINEERING CỦA THẦY (Giữ nguyên gốc)
    prompt_engineering = (r"""
# 🚨 QUY TẮC HIỂN THỊ
1. TUYỆT ĐỐI KHÔNG trích dẫn nguyên văn các thẻ XML (<co_ban>, <huong_dan_giai>...) ra màn hình.
2. Bạn là Thầy giáo, hãy dùng ngôn ngữ giảng bài tự nhiên, đẹp mắt qua Markdown và LaTeX.
3. Chỉ dùng kiến thức trong "KHO TRI THỨC" bên dưới. Nếu thiếu, báo [MISSING_DOC].

# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS, hoạt động theo kiến thức chương trình GDPT 2018, lưu ý hãy sử dụng danh pháp quốc tế theo chương trình GDPT 2018. 
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em". 
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm trường Phan Chu Trinh.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING 3 CẤP ĐỘ)
Khi học sinh hỏi bài tập, bạn không được giải ngay. Hãy thực hiện theo quy trình:
- Lựa chọn A: Hướng dẫn tư duy từng bước.
- Lựa chọn B: Đưa ra "bản đồ" giải bài.
- Lựa chọn C: Đưa bài giải chi tiết.

# 📐 QUY TẮC HIỂN THỊ & LATEX
- Công thức: bọc trong $...$ hoặc $$...$$. IUPAC chuẩn 2018.
    """)

    full_instruction = prompt_engineering + "\n\n# 📚 KHO TRI THỨC:\n" + knowledge_base

    try:
        # Dùng gemini-1.5-flash để ổn định và hạn mức cao cho người dùng trả phí
        chat = client.chats.create(
            model="gemini-1.5-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.1)
        )
        return client, chat, len(knowledge_base)
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 📌 4. SIDEBAR & HIỂN THỊ CHAT
# ==================================================
with st.sidebar:
    if total_chars > 0:
        st.success(f"✅ Đã nạp {total_chars} ký tự tri thức.")
    else:
        st.error("❌ 0 ký tự: Thầy kiểm tra lại thư mục 'files' nhé!")

    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung")
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")

# Container hiển thị chat
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# KHUNG NHẬP LIỆU (Luôn hiện ở cuối trang)
st.markdown("---")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="fixed_uploader")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 📌 5. XỬ LÝ TIN NHẮN
# ==================================================
if prompt:
    if client is None:
        st.error("⚠️ Thầy kiểm tra lại API Key trong phần Secrets nhé!")
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
                        time.sleep(1) # Nghỉ 1 giây để tránh 429
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
