import streamlit as st
from google import genai
from google.genai import types
import os
import json 
import time

# ==================================================
# 📌 1. CẤU HÌNH HỆ THỐNG
# ==================================================
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác không?"
HARDCODED_GREETING = "Xin chào em, thầy là Gia sư Hoá học trường Phan Chu Trinh. Thầy đã sẵn sàng đồng hành cùng em rồi đây!"

def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
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

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# ⚙️ 3. CẤU HÌNH CHAT SESSION (PHIÊN BẢN 2.0 FLASH LITE)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    # Để mặc định để SDK tự chọn phiên bản API ổn định nhất (Hết lỗi 404/400)
    client = genai.Client(api_key=api_key)
    
    # Quét tài liệu từ thư mục 'files'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(current_dir, "files")
    knowledge_base = ""
    if os.path.exists(files_dir):
        for filename in os.listdir(files_dir):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join(files_dir, filename), "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- DỮ LIỆU TỪ FILE {filename} ---\n" + f.read()
                except: pass

    # --- GIỮ NGUYÊN TOÀN BỘ PROMPT CỦA THẦY ---
    sys_instruct = (r"""
# 🚨 QUY TẮC HIỂN THỊ (QUAN TRỌNG NHẤT)
1. TUYỆT ĐỐI KHÔNG hiển thị các thẻ XML như <co_ban>, <huong_dan_giai>, <bai_giai_chi_tiet> ra màn hình.
2. BẠN LÀ THẦY GIÁO, KHÔNG PHẢI MÁY TRÍCH XUẤT. Hãy diễn đạt lại kiến thức bằng ngôn ngữ giảng bài tự nhiên, đẹp mắt qua Markdown và LaTeX.
3. Chỉ dùng kiến thức trong "KHO TRI THỨC" bên dưới. Nếu thiếu, báo [MISSING_DOC].

# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" môn Hóa học THCS trường Phan Chu Trinh. Xưng "Thầy", gọi "Em".
Hoạt động theo chương trình GDPT 2018, sử dụng danh pháp quốc tế (Aluminium, Oxide...).

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
Khi học sinh hỏi bài tập:
- Bước 1: Đưa ra 3 lựa chọn A (Tư duy), B (Bản đồ giải), C (Đáp án chi tiết).
- Bước 2: Dẫn dắt, khích lệ em tự làm, tuyệt đối không tính hộ phép tính.

# 📐 QUY TẮC LATEX
- Công thức: bọc trong $...$ hoặc $$...$$.
    """)

    full_instruction = sys_instruct + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP:\n" + knowledge_base

    try:
        # THAY ĐỔI DUY NHẤT: CHUYỂN SANG MODEL 2.0 FLASH LITE
        chat = client.chats.create(
            model="gemini-2.0-flash-lite", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.0)
        )
        return client, chat, len(knowledge_base)
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}")
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 🎨 4. SIDEBAR & GIAO DIỆN HIỂN THỊ
# ==================================================
with st.sidebar:
    if total_chars > 0:
        st.success(f"✅ Đã nạp {total_chars} ký tự tri thức.")
    else:
        st.error("❌ Chưa tìm thấy file tài liệu trong thư mục 'files'.")

    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung")
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")

# Hiển thị tin nhắn
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
# Khung nhập liệu (Luôn hiện ở dưới cùng)
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"])
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 🚀 5. XỬ LÝ LOGIC (BẢN FIX TRIỆT ĐỂ 429)
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa kết nối được. Thầy kiểm tra lại API Key nhé!")
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
                        # Khoảng nghỉ tránh lỗi 429 tức thời
                        time.sleep(1) 
                        message_parts.append(types.Part.from_text(text=cleaned_prompt))
                        
                        response = None
                        # Cơ chế tự động thử lại nếu đường truyền bị nghẽn
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
                        
                        # Xử lý báo thiếu tài liệu
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
                        st.error(f"Hệ thống đang bận một chút, em đợi 10 giây rồi thử lại nhé! (Lỗi: {e})")
