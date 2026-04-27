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
# Lời chào đúng tinh thần trường Phan Chu Trinh
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
# ⚙️ 2. CẤU HÌNH AI (BẢN "NỒI ĐỒNG CỐI ĐÁ")
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None

    # QUAN TRỌNG: KHÔNG thêm http_options để tránh lỗi 404/400
    client = genai.Client(api_key=api_key)
    
    # --- LỆNH ĐIỀU HÀNH GDPT 2018 ---
    sys_instruct = (r"""
# 🎭 VAI TRÒ
Bạn là "Gia sư ảo" môn Hóa học THCS (lớp 8, 9) và Sinh học (lớp 6) tại trường Phan Chu Trinh.
Xưng "Thầy", gọi "Em". Ngôn ngữ ấm áp, gần gũi nhưng chuẩn mực sư phạm.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. DANH PHÁP: Sử dụng 100% tiếng Anh IUPAC (Aluminium, Hydrogen, Iron(III) oxide...). KHÔNG dùng tên cũ như Sắt, Nhôm, Đồng.
2. ĐIỀU KIỆN CHUẨN (ĐKC): Mặc định sử dụng hằng số $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
3. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng số $22,4 \text{ L/mol}$ khi học sinh yêu cầu cụm từ "Điều kiện tiêu chuẩn".
4. ĐƠN VỊ: Dùng amu cho khối lượng nguyên tử, bar cho áp suất.

# 🎓 CHIẾN LƯỢC SƯ PHẠM
- LÝ THUYẾT: Trả lời ngay, ngắn gọn, dễ hiểu.
- BÀI TẬP: Hỏi em muốn "Hướng dẫn từng bước" hay "Xem bài giải chi tiết". Khích lệ em tự làm bài.

# 📐 TRÌNH BÀY
- Đề mục lớn (I, II, III...) và bước nhỏ (1, 2, 3...) phải IN ĐẬM và đứng riêng một dòng.
- PTHH: Nằm trên dòng riêng, bọc trong $$...$$. 
- Các PTHH không được viết dính nhau. Công thức bọc trong $...$.
    """)

    try:
        # Dùng gemini-1.5-flash để có hạn mức (Quota) cao nhất cho tài khoản Tier 1
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
# 🎨 3. GIAO DIỆN CHAT
# ==================================================
with st.sidebar:
    st.header("⚙️ Trạng thái")
    st.success("✅ Chuẩn: GDPT 2018")
    st.info("💡 $V_m = 24,79 \text{ L/mol}$")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.rerun()

# Container hiển thị hội thoại
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
# Khung nhập ảnh và văn bản
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="file_up")
prompt = st.chat_input("Hỏi thầy về Hóa học/Sinh học đi em...")

# ==================================================
# 🚀 4. XỬ LÝ GỬI TIN NHẮN (CƠ CHẾ TỰ ĐỘNG THỬ LẠI)
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
                        # Tự động thử lại 3 lần nếu Google báo bận (429)
                        response = None
                        for attempt in range(3):
                            try:
                                response = chat_session.send_message(message_parts)
                                break
                            except Exception as e:
                                if "429" in str(e) and attempt < 2:
                                    time.sleep(5) # Đợi 5 giây rồi thử lại
                                    continue
                                else: raise e

                        if response:
                            res_text = response.text.strip()
                            st.markdown(res_text)
                            st.session_state.messages.append({"role": "assistant", "content": res_text})
                            save_data(HISTORY_FILE, st.session_state.messages)
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hệ thống bận, em đợi 10 giây rồi nhấn gửi lại giúp thầy nhé! (Lỗi: {e})")
