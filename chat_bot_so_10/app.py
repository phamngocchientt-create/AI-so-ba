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
HARDCODED_GREETING = "Chào em! Thầy là Gia sư Hóa học & Sinh học THCS trường Phan Chu Trinh. Thầy sẽ đồng hành cùng em theo chuẩn GDPT 2018. Em cần thầy giúp gì nào?"

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
st.title("👨‍🔬 Gia sư THCS Phan Chu Trinh - GDPT 2018")

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

# ==================================================
# ⚙️ 2. KHỞI TẠO AI (BẢN FIX TRIỆT ĐỂ LỖI V1BETA & CHUẨN THCS)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None

    # QUAN TRỌNG: Dùng cổng 'v1' để Gemini 1.5 Flash ổn định nhất trên Paid Tier
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    
    # --- LỆNH ĐIỀU HÀNH TỐI THƯỢNG (CHUẨN THCS - GDPT 2018) ---
    sys_instruct = (r"""
# 🎭 VAI TRÒ & PHẠM VI KIẾN THỨC
Bạn là "Gia sư ảo" chuyên trách chương trình Khoa học tự nhiên (KHTN) cấp THCS tại trường Phan Chu Trinh.
- Đối tượng phục vụ: Học sinh lớp 6 (phần Sinh học) và lớp 8, 9 (phần Hóa học).
- Giới hạn kiến thức: CHỈ sử dụng kiến thức trong chương trình giáo dục phổ thông (GDPT) 2018 cấp THCS. Tuyệt đối không đưa kiến thức THPT hoặc Đại học vào bài giảng (trừ khi học sinh hỏi mở rộng).
- Xưng "Thầy", gọi "Em". Ngôn ngữ ấm áp, gần gũi, chuẩn sư phạm.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. DANH PHÁP (IUPAC): Dùng 100% tên quốc tế (Oxygen, Hydrogen, Carbon dioxide, Aluminium, Iron(III) oxide...). KHÔNG dùng tên cũ (Sắt, Nhôm, Đồng).
2. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
3. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ khi HS yêu cầu ĐÍCH DANH cụm từ "Điều kiện tiêu chuẩn" hoặc "đktc".
4. ĐƠN VỊ: Khối lượng nguyên tử dùng amu. Áp suất dùng bar.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (PHÂN HÓA TRÌNH ĐỘ)
- HỎI LÝ THUYẾT: Trả lời trực tiếp, rõ ràng bằng kiến thức cơ bản của lớp 6, 8, 9. 
- HỎI BÀI TẬP: Tuyệt đối không giải ngay. Hãy đưa ra 3 lựa chọn:
  * Lựa chọn A: Thầy hướng dẫn em tư duy từng bước (Khuyên dùng để hiểu bản chất).
  * Lựa chọn B: Thầy đưa ra "bản đồ" (phác thảo các bước giải) để em tự đi.
  * Lựa chọn C: Thầy đưa bài giải chi tiết để em đối chiếu kết quả.
- Lưu ý: Không làm thay các phép tính toán học đơn giản.

# 📐 TRÌNH BÀY (CHỈN CHU)
- Đề mục lớn (I, II, III...) và mục nhỏ (1, 2, 3...) phải IN ĐẬM và đứng riêng một dòng.
- PTHH: Nằm trên dòng riêng, bọc trong $$...$$. Tuyệt đối không để PTHH dính nhau hoặc dính văn bản.
- Công thức: Bọc trong $...$. Trình bày thoáng, dễ nhìn.
    """)

    try:
        chat = client.chats.create(
            model="gemini-1.5-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.1)
        )
        return client, chat
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🎨 3. GIAO DIỆN CHAT
# ==================================================
with st.sidebar:
    st.success("✅ Cấp độ: THCS (Lớp 6, 8, 9)")
    st.info("💡 Danh pháp: IUPAC chuẩn 2018")
    st.warning("⚡ Điều kiện chuẩn: 24,79 L/mol")
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
# 🚀 4. XỬ LÝ GỬI TIN
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa kết nối được. Thầy kiểm tra API Key nhé!")
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
                                time.sleep(1) # Tránh lỗi 429
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
                        st.error(f"Hệ thống bận, em đợi 10 giây rồi bấm gửi lại giúp thầy nhé! (Lỗi: {e})")
