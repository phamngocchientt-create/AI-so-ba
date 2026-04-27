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
HARDCODED_GREETING = "Chào em! Thầy là Gia sư Hóa học & Sinh học THCS trường Phan Chu Trinh. Thầy đã sẵn sàng đồng hành cùng em theo chuẩn GDPT 2018 rồi đây!"

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

st.set_page_config(page_title="Gia sư THCS Phan Chu Trinh", layout="wide")
st.title("👨‍🔬 Gia sư THCS Phan Chu Trinh - GDPT 2018")

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ 2. KHỞI TẠO AI (BẢN FIX LỖI 400 & 404 & 429)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None

    # SỬA LỖI 400: Dùng v1beta là cổng chuẩn nhất cho system_instruction trong SDK v2
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # --- LỆNH ĐIỀU HÀNH TỐI THƯỢNG (CHUẨN THCS - GDPT 2018) ---
    sys_instruct = (r"""
# 🎭 VAI TRÒ & PHẠM VI
Bạn là "Gia sư ảo" chuyên môn KHTN (Hóa học 8-9, Sinh học 6) tại trường Phan Chu Trinh.
- Đối tượng: Học sinh THCS.
- Giới hạn: CHỈ dùng kiến thức trong chương trình GDPT 2018 cấp THCS. Không dùng kiến thức cấp 3.
- Xưng "Thầy", gọi "Em". Ngôn ngữ ấm áp, đúng chuẩn sư phạm.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018
1. DANH PHÁP (IUPAC): Dùng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Oxide...). KHÔNG dùng tên cũ.
2. ĐIỀU KIỆN CHUẨN (ĐKC): Mặc định dùng hằng số $24,79 \text{ L/mol}$.
3. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ khi HS yêu cầu đích danh.
4. ĐƠN VỊ: Khối lượng nguyên tử dùng amu, áp suất dùng bar.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
- BÀI TẬP: Tuyệt đối không giải ngay. Hãy đưa ra 3 lựa chọn:
  * Lựa chọn A: Thầy hướng dẫn em tư duy từng bước.
  * Lựa chọn B: Thầy đưa ra "bản đồ" các bước giải.
  * Lựa chọn C: Thầy đưa bài giải chi tiết để đối chiếu.
- Khuyến khích em tự tính toán, không làm thay phép tính cơ bản.

# 📐 TRÌNH BÀY
- Đề mục lớn (I, II, III...) và mục nhỏ (1, 2, 3...) phải IN ĐẬM và đứng riêng dòng.
- PTHH: Nằm trên dòng riêng, bọc trong $$...$$. Tuyệt đối không để PTHH dính nhau.
- Công thức: Bọc trong $...$.
    """)

    try:
        # Dùng gemini-1.5-flash để có hạn mức cao nhất, tránh 429
        chat = client.chats.create(
            model="gemini-1.5-flash", 
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.1
            )
        )
        return client, chat
    except Exception as e:
        st.error(f"⚠️ Lỗi khởi tạo: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🎨 3. GIAO DIỆN CHAT
# ==================================================
with st.sidebar:
    st.success("✅ Cấp độ: THCS (Lớp 6, 8, 9)")
    st.info("💡 Hằng số khí: $24,79 \text{ L/mol}$")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.rerun()

chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="file_up")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 🚀 4. XỬ LÝ GỬI TIN (CHỐNG LỖI 429)
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa kết nối. Thầy kiểm tra API Key nhé!")
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
                with st.spinner("Thầy đang suy nghĩ..."):
                    try:
                        response = None
                        for attempt in range(3):
                            try:
                                time.sleep(1) # Nghỉ để tránh 429
                                response = chat_session.send_message(message_parts)
                                break
                            except Exception as e:
                                if "429" in str(e) and attempt < 2:
                                    time.sleep(5)
                                    continue
                                else: raise e

                        if response:
                            res_text = response.text.strip()
                            st.markdown(res_text)
                            st.session_state.messages.append({"role": "assistant", "content": res_text})
                            save_data(HISTORY_FILE, st.session_state.messages)
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hệ thống bận, em đợi 10 giây rồi thử lại nhé! (Lỗi: {e})")
