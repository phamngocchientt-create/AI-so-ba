import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 

# ==================================================
# 📌 CẤU HÌNH HỆ THỐNG
# ==================================================
LIST_FILES = ['files/frs2tgz7ga81', 'files/l6xlew9a4ibx']
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json"  # File mới để lưu lịch sử chat
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

# --- HÀM XỬ LÝ JSON (Chống mất dữ liệu) ---
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
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

# Khởi tạo trạng thái từ FILE thay vì RAM trống
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    
    # Nút xóa lịch sử (Dành cho học sinh muốn bắt đầu lại)
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
# ⚙️ CẤU HÌNH CHAT SESSION (NẠP TÀI LIỆU 1 LẦN)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None 

    client = genai.Client(api_key=api_key)
    
    # Giữ nguyên System Instruction tâm huyết của bạn
    sys_instruct = (r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Khoa học tự nhiên (phân môn Hóa học 8-9 và Sinh học 6) tại trường Phan Chu Trinh.
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình GDPT 2018 cấp THCS. Tuyệt đối không đưa kiến thức THPT/Đại học vào bài giảng.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Iron(III) oxide, Sulfate...). TUYỆT ĐỐI KHÔNG dùng tên cũ (Sắt, Nhôm, Đồng).
3. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
4. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ khi HS yêu cầu ĐÍCH DANH.
5. ĐƠN VỊ: Khối lượng nguyên tử dùng "amu". Áp suất dùng "bar".

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
1. CÂU HỎI LÝ THUYẾT: 
   - Trả lời trực tiếp, rõ ràng. Nếu em hỏi kiến thức cơ bản, dùng kiến thức cơ bản. Nếu em hỏi "tại sao", mới dùng kiến thức giải thích sâu.
2. CÂU HỎI BÀI TẬP (TÍNH TOÁN/LÝ THUYẾT): 
   - Tuyệt đối không giải ngay. Hãy chào đón và đưa ra 3 lựa chọn:
     * Lựa chọn A: Thầy hướng dẫn em tư duy từng bước (Khuyên dùng).
     * Lựa chọn B: Thầy đưa ra "bản đồ" (phác thảo các bước giải) để em tự đi.
     * Lựa chọn C: Thầy đưa bài giải chi tiết để em đối chiếu.
   - Nếu em chọn C hoặc yêu cầu khẩn thiết, đưa bài giải đầy đủ lời giải, công thức và phép tính (Không ghi Bước 1, Bước 2...).

# 📐 QUY TẮC HIỂN THỊ & TRÌNH BÀY (CỰC KỲ QUAN TRỌNG)
Để câu trả lời đẹp như "viết bảng", bạn PHẢI tuân thủ:
1. KHOẢNG TRẮNG: Sử dụng "Dòng trống" (Double Enter) giữa các đoạn văn, giữa đề mục và nội dung.
2. ĐỀ MỤC: Các mục lớn (I, II, III...), mục nhỏ (a, b, c...) hoặc số thứ tự (1, 2, 3...) phải **IN ĐẬM** và đứng riêng một dòng.
3. PHƯƠNG TRÌNH HÓA HỌC (PTHH):
   - Phải bọc trong $$...$$ và nằm trên dòng riêng biệt.
   - Mỗi PTHH là một dòng riêng. Tuyệt đối không để 2 PTHH trên cùng 1 dòng.
   - Giữa các PTHH liên tiếp phải có một dòng trống.
4. CÔNG THỨC & LATEX:
   - Công thức hóa học/toán học bọc trong $...$ (cùng dòng) hoặc $$...$$ (riêng dòng).
   - Ví dụ: $Al_2O_3$, $n = \frac{m}{M}$.
   - Không dùng ký hiệu lạ như \ce, \text. Tách chữ và số rõ ràng.

# ❤️ PHONG CÁCH & KẾT THÚC
- Luôn khích lệ: "Thầy tin em làm được", "Giỏi lắm", "Cố gắng lên nhé".
- Kết thúc: Luôn bằng một câu hỏi gợi mở hoặc kiểm tra sự thấu hiểu của học sinh.
    """)

    try:
        chat = client.chats.create(
            model="gemini-2.5-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.2)
        )
        
        # Nạp tài liệu vào phiên chat ngay từ đầu
        list_parts = []
        for file_id in LIST_FILES:
            uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_id}"
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain"))
        
        list_parts.append(types.Part.from_text(text="Nạp tài liệu. Chỉ trả lời dựa trên đây. Nếu thiếu dùng mã [MISSING_DOC]."))
        chat.send_message(list_parts)
        return client, chat
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🤖 GIAO DIỆN VÀ XỬ LÝ TIN NHẮN (ĐÃ CẬP NHẬT CỐ ĐỊNH VỊ TRÍ)
# ==================================================

# 1. Tạo container cho lịch sử chat - Container này phải nằm TRÊN khung upload
chat_placeholder = st.container()

# 2. Hiển thị lịch sử chat từ file/session vào trong container
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 3. Khu vực nhập liệu luôn nằm DƯỚI container chat
st.markdown("---")
# Đặt file_uploader ở đây để nó luôn xuất hiện sau cùng của đoạn chat
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="fixed_bottom_uploader")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# 4. Xử lý logic khi có câu hỏi mới
if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    message_parts = []
    
    # Xử lý nội dung User (Có ảnh hoặc không)
    user_msg_content = cleaned_prompt
    if uploaded_file:
        image_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type)
        message_parts.append(image_part)
        user_msg_content = f"📝 (Kèm ảnh) {cleaned_prompt}"
    
    # Lưu vào lịch sử (RAM + FILE)
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)

    # Hiển thị câu hỏi mới vào container chat ngay lập tức
    with chat_placeholder:
        with st.chat_message("user"):
            if uploaded_file: st.image(uploaded_file, width=300)
            st.markdown(cleaned_prompt)

        # Xử lý phản hồi của Assistant
        with st.chat_message("assistant"):
            with st.spinner("Thầy đang xem bài..."):
                try:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
                    response = chat_session.send_message(message_parts)
                    res_text = response.text.strip()
                    
                    if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                        if cleaned_prompt not in st.session_state.missing_questions:
                            st.session_state.missing_questions.append(cleaned_prompt)
                            save_data(STORAGE_FILE, st.session_state.missing_questions)
                        final_res = ERROR_MESSAGE
                    else:
                        final_res = res_text

                    st.markdown(final_res)
                    # Lưu phản hồi thầy vào lịch sử
                    st.session_state.messages.append({"role": "assistant", "content": final_res})
                    save_data(HISTORY_FILE, st.session_state.messages)
                    
                    # Rerun để dọn dẹp khung upload và đẩy lịch sử chat lên trên khung input
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Lỗi: {e}")









