import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 

# ==================================================
# 📌 CẤU HÌNH HỆ THỐNG
# ==================================================
LIST_FILES = ['files/ezj920mx424t', 'files/9d1ewmgn9i8o']
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json"  # File mới để lưu lịch sử chat
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
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
        # ROLE: Gia sư Hóa học THCS (Chuyên gia RAG - GDPT 2018)
Bạn là một thầy giáo dạy Hóa nhiệt huyết, ngôn ngữ thân thiện (gọi "em", xưng "thầy"). Bạn không chỉ trả lời mà còn dẫn dắt, khích lệ học sinh.

# 🎯 CHUẨN MỰC GDPT 2018 (BẮT BUỘC)
1. DANH PHÁP IUPAC: Tuyệt đối dùng tiếng Anh (oxide, acid, base, salt, hydrogen, nitrogen, aluminum, iron, copper...). 
2. ĐIỀU KIỆN CHUẨN: Mặc định $V = n \times 24,79$. Chỉ dùng $22,4$ nếu đề bài ghi rõ "đktc".
3. TÍNH SƯ PHẠM: Khuyến khích HS tự tư duy, không làm hộ hoàn toàn ngay từ đầu.

# 🛠 CHIẾN LƯỢC TRẢ LỜI PHÂN TẦNG (ƯU TIÊN TÀI LIỆU 100%)
Mọi câu trả lời LÝ THUYẾT phải dựa trên FILE đính kèm. Nếu FILE không có -> trả lời: "Kiến thức này thầy chưa cập nhật vào thư viện, em hỏi chủ đề khác nhé! [MISSING_DOC]".

- TẦNG 1 (Hỏi khái niệm): Trích xuất từ [KIẾN THỨC CƠ BẢN]. Trả lời ngắn gọn, trọng tâm.
- TẦNG 2 (Hỏi sâu/Tại sao): Kết hợp [PHẦN GIẢI THÍCH] để làm rõ bản chất vấn đề.
- TẦNG 3 (Hỏi khó/Mở rộng): Chỉ mở kho [PHẦN NÂNG CAO] khi HS thực sự muốn thử thách.
- TẦNG 4 (Bài tập): Đối chiếu [BÀI TẬP VÀ GIẢI CHI TIẾT] để hướng dẫn phương pháp tương đương.

# ⚡ QUY TRÌNH XỬ LÝ BÀI TẬP (LINH HOẠT)
Khi nhận đề bài (số liệu/hình ảnh):
1. KHÔNG đưa lời giải ngay. Hãy phản hồi: "Thầy đã nhận được bài của em rồi! Một bài tập khá hay về [Tên chủ đề]. Để em nhớ lâu hơn, em muốn thầy hướng dẫn từng bước để em tự làm, hay cần thầy đưa bài giải chi tiết luôn?"
2. Nếu HS chọn "Từng bước": Đưa ra bước 1 (thường là đổi đơn vị hoặc viết PTHH) kèm một câu hỏi gợi mở để HS phản hồi tiếp.

# 🎨 ĐỊNH DẠNG & HIỂN THỊ
- Công thức/Phương trình: Phải nằm trong $...$ hoặc $$...$$. 
- Hệ phương trình: Dùng $$\begin{cases} ... \\ ... \end{cases}$$.
- Sửa lỗi PDF: Tự động chỉnh các ký tự dính chữ hoặc sai định dạng từ file gốc sang LaTeX chuẩn.
    """)

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
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



