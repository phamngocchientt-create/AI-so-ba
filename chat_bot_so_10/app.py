import streamlit as st
from google import genai
from google.genai import types
import os
import json 
import time

# ==================================================
# 📌 1. CẤU HÌNH HỆ THỐNG
# ==================================================
HISTORY_FILE = "chat_history.json" 
HARDCODED_GREETING = "Chào em! Thầy là Gia sư Hoá học trường Phan Chu Trinh. Thầy đồng hành cùng em theo chuẩn GDPT 2018. Em cần thầy giúp gì nào?"

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

st.set_page_config(page_title="Gia sư Hóa học Phan Chu Trinh", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Chuẩn GDPT 2018")

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ 2. CẤU HÌNH AI (MODEL 1.5 FLASH - QUOTA CAO NHẤT)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None

    # Khởi tạo Client mặc định
    client = genai.Client(api_key=api_key)
    
    # --- PROMPT ÉP KHUÔN GDPT 2018 ---
    sys_instruct = (r"""
# 🎭 VAI TRÒ
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS (lớp 8, 9) và Sinh học (lớp 6), làm việc tại trường Phan Chu Trinh.
Xưng "Thầy", gọi "Em". Ngôn ngữ ấm áp, đúng chuẩn sư phạm.

# 📖 QUY TẮC CHUYÊN MÔN GDPT 2018
1. DANH PHÁP: Dùng 100% tiếng Anh IUPAC (Aluminium, Hydrogen, Iron(III) oxide...). KHÔNG dùng tên cũ.
2. ĐIỀU KIỆN CHUẨN (ĐKC): Mặc định hằng số $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
3. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ nếu học sinh nhắc đích danh cụm từ này.
4. ĐƠN VỊ: Dùng amu cho khối lượng nguyên tử, bar cho áp suất (theo SGK mới).

# 🎓 CHIẾN LƯỢC GIẢNG DẠY
- CÂU HỎI LÝ THUYẾT: Trả lời ngay bằng kiến thức GDPT 2018.
- BÀI TẬP: Hỏi HS muốn hướng dẫn (scaffolding) hay xem giải chi tiết. Khuyến khích HS tự làm.

# 📐 TRÌNH BÀY
- In đậm (**) các đề mục lớn (I, II, III...) và các bước (1, 2, 3...). Các mục này phải đứng riêng dòng.
- PTHH: Nằm trên dòng riêng, bọc trong $$...$$. Công thức bọc trong $...$.
    """)

    try:
        # Ép dùng gemini-1.5-flash để thoát lỗi 429 do đây là model có quota Tier 1 cao nhất
        chat = client.chats.create(
            model="gemini-1.5-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.1)
        )
        return client, chat
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối AI: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🎨 3. GIAO DIỆN & SIDEBAR
# ==================================================
with st.sidebar:
    st.header("⚙️ Trạng thái")
    st.success("✅ Chế độ: GDPT 2018 (IUPAC)")
    st.info("💡 Hằng số: $24,79 \text{ L/mol}$")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.rerun()

# Hiển thị tin nhắn
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="file_up")
prompt = st.chat_input("Hỏi thầy đi em...")

# ==================================================
# 🚀 4. XỬ LÝ GỬI TIN NHẮN (CƠ CHẾ RETRY MẠNH MẼ)
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa khởi động. Thầy kiểm tra lại API Key nhé!")
    else:
        cleaned_prompt = prompt.strip()
        message_parts = [types.Part.from_text(text=cleaned_prompt)]
        
        if uploaded_file:
            image_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type)
            message_parts.append(image_part)
        
        st.session_state.messages.append({"role": "user", "content": cleaned_prompt})
        save_data(HISTORY_FILE, st.session_state.messages)

        with chat_placeholder:
            with st.chat_message("user"):
                if uploaded_file: st.image(uploaded_file, width=300)
                st.markdown(cleaned_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thầy đang xem bài..."):
                    try:
                        # Tự động thử lại 3 lần, thời gian chờ tăng dần (Backoff)
                        response = None
                        for attempt in range(3):
                            try:
                                response = chat_session.send_message(message_parts)
                                break
                            except Exception as e:
                                if "429" in str(e) and attempt < 2:
                                    time.sleep(3 * (attempt + 1)) # Đợi 3s, sau đó 6s
                                    continue
                                else: raise e

                        if response:
                            res_text = response.text.strip()
                            st.markdown(res_text)
                            st.session_state.messages.append({"role": "assistant", "content": res_text})
                            save_data(HISTORY_FILE, st.session_state.messages)
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hệ thống bận, em đợi 5 giây rồi nhấn gửi lại giúp thầy nhé! (Lỗi: {e})")
