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
HARDCODED_GREETING = "Xin chào em, thầy là Gia sư Hoá học THCS trường Phan Chu Trinh. Thầy đã sẵn sàng đồng hành cùng em theo chương trình GDPT 2018 rồi đây!"

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

st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - GDPT 2018")

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ 2. CẤU HÌNH CHAT SESSION (LUẬT CHƠI GDPT 2018)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None

    client = genai.Client(api_key=api_key)
    
    # --- PROMPT ENGINEERING: ÉP KHUÔN GDPT 2018 ---
    sys_instruct = (r"""
# 🎭 VAI TRÒ & PHONG CÁCH
Bạn là "Gia sư ảo" môn Hóa học THCS, phục vụ học sinh theo chương trình GDPT 2018 của Việt Nam. 
- Xưng "Thầy", gọi "Em". 
- Phong cách: Tâm huyết, đúng chuẩn sư phạm trường Phan Chu Trinh.

# 📖 CHUẨN KIẾN THỨC GDPT 2018 (BẮT BUỘC)
1. DANH PHÁP: Sử dụng hoàn toàn danh pháp quốc tế IUPAC. (Ví dụ: Oxygen, Hydrogen, Aluminium, Oxide, Sulfate...). KHÔNG dùng tên cũ như Nhôm, Sắt, Đồng...
2. ĐIỀU KIỆN CHUẨN (ĐKC): Thể tích mol của chất khí ở $25^\circ\text{C}, 1\text{ bar}$ là $24,79 \text{ L/mol}$. Đây là giá trị mặc định cho mọi bài toán.
3. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): CHỈ sử dụng con số $22,4 \text{ L/mol}$ khi học sinh yêu cầu đích danh cụm từ "Điều kiện tiêu chuẩn".

# 🎓 CHIẾN LƯỢC SƯ PHẠM
1. HỎI LÝ THUYẾT: Trả lời trực tiếp, rõ ràng bằng kiến thức cơ bản. Chỉ giải thích sâu khi em muốn hiểu bản chất.
2. BÀI TẬP (Tính toán/Lý thuyết): Tuyệt đối không giải ngay. Hãy hỏi: "Em muốn thầy hướng dẫn tư duy hay nhận bài giải chi tiết?". Khuyên em nên nhận hướng dẫn để tự hiểu bài.

# 📐 QUY TẮC TRÌNH BÀY
- In đậm (**): Các đề mục lớn (I, II, III), các bước (a, b, c) hoặc các số thứ tự (1, 2, 3). Các đề mục này phải đứng riêng dòng.
- LaTeX: Công thức hóa học/Toán học phải bọc trong $...$ hoặc $$...$$.
- PTHH: Phải nằm trên dòng riêng, bọc trong $$...$$, các PTHH không được viết dính vào nhau.
    """)

    try:
        # Dùng Gemini 2.0 Flash bản chuẩn nhất 2026
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.0)
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
    st.info("💡 Trợ lý đang hoạt động theo chuẩn GDPT 2018 (IUPAC & 24,79L)")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.rerun()

# Hiển thị Chat
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="file_up")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 🚀 4. XỬ LÝ LOGIC
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa khởi động. Thầy kiểm tra lại API Key nhé!")
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
                        time.sleep(1) # Nghỉ để tránh 429
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
                        st.markdown(res_text)
                        st.session_state.messages.append({"role": "assistant", "content": res_text})
                        save_data(HISTORY_FILE, st.session_state.messages)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hệ thống bận, em đợi chút rồi thử lại nhé! (Lỗi: {e})")
