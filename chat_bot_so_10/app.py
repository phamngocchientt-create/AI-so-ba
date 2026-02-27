import streamlit as st
from google import genai
from google.genai import types
import os
import json 
from datetime import datetime

# ==================================================
# 📌 CẤU HÌNH FILE & BIẾN HỆ THỐNG
# ==================================================
LIST_FILES = ['files/suw8ark9dxlc', 'files/iykl36ub3fzf']
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" # Lưu lịch sử để không bị mất khi web reload
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

# --- HÀM XỬ LÝ LƯU TRỮ CÂU HỎI THIẾU ---
def load_missing_questions():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def save_missing_questions(questions_list):
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions_list, f, ensure_ascii=False, indent=4)

# --- HÀM XỬ LÝ LỊCH SỬ CHAT (CHỐNG MẤT TIN NHẮN) ---
def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return [{"role": "assistant", "content": HARDCODED_GREETING}]

def save_chat_history(messages):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

# ==================================================
# 🏗️ KHỞI TẠO ỨNG DỤNG
# ==================================================
st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

# Khởi tạo trạng thái từ FILE thay vì RAM
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_missing_questions()

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# --- SIDEBAR QUẢN LÝ ---
with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_chat_history(st.session_state.messages)
        st.rerun()

    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung")
    
    # Hiển thị danh sách câu hỏi lỗi
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
        
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            if st.form_submit_button("Xóa Toàn bộ Log"):
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    st.session_state.missing_questions = []
                    save_missing_questions([])
                    st.success("✅ Đã dọn dẹp!")
                    st.rerun()
                else: st.error("❌ Sai mật khẩu.")
    else:
        st.write("Không có câu hỏi nào cần bổ sung.")

# --- CẤU HÌNH CHAT SESSION (CHỈ CHẠY 1 LẦN) ---
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None 

    client = genai.Client(api_key=api_key)
    # Giữ nguyên prompt cũ của bạn nhưng giảm temperature để bot bớt "chém gió"
    sys_instruct = (r"""
        Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018, bạn sẽ thực hiện đúng theo quy tắc được người lập trình đưa ra.
        
   [QUY TẮC HIỂN THỊ - CHỐNG DÍNH CHỮ]:
        3. Hệ phương trình BẮT BUỘC dùng cấu trúc chuẩn:
           $$ \begin{cases} pt1 \\ pt2 \end{cases} $$
        4. Tự động sửa lỗi hiển thị từ PDF (ví dụ: 'H2SO4' -> $H_2SO_4$, 'n = m/M' -> $n = \frac{m}{M}$).

        [QUY TẮC PHÂN TẦNG - CHỐNG "QUÁ NHIỆT TÌNH"]:
        Bạn có 4 vùng học liệu: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], [BÀI TẬP].
        - Nếu HS hỏi khái niệm chung: CHỈ trích dẫn từ [KIẾN THỨC CƠ BẢN]. Tuyệt đối không tự ý lấy thêm phần Giải thích hay Nâng cao.
        - Chỉ khi HS hỏi "Tại sao?", "Rõ hơn" mới dùng [PHẦN GIẢI THÍCH].
        - Chỉ khi HS hỏi câu khó/mở rộng mới dùng [PHẦN NÂNG CAO].

    [QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] 
    Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].

    A. QUY TẮC NGUỒN (RAG) & GIỚI HẠN TUYỆT ĐỐI: (ƯU TIÊN SỐ 1)
    1. ƯU TIÊN TUYỆT ĐỐI: CHỈ trả lời các câu hỏi LÝ THUYẾT (định nghĩa, tính chất, phân loại) DỰA TRÊN THÔNG TIN TÌM THẤY trong tài liệu đính kèm.
    2. QUY TẮC TỪ CHỐI BẮT BUỘC: Nếu thông tin LÝ THUYẾT KHÔNG được tìm thấy trong tài liệu đính kèm, TUYỆT ĐỐI KHÔNG sử dụng kiến thức nền tảng của bạn. BẮT BUỘC trả lời kèm mã lỗi [MISSING_DOC] ở cuối câu.
    3. TUYỆT ĐỐI KHÔNG sử dụng kiến thức Hóa học Cấp 3 hoặc Đại học để trả lời.

    B. QUY TẮC TRẢ LỜI LÝ THUYẾT (PHÂN TẦNG):
    1. Mặc định (Hỏi lý thuyết chung): CHỈ trích dẫn thông tin từ mục **[KIẾN THỨC CƠ BẢN]**.
    2. Giải thích sâu (Khi HS hỏi "Tại sao", "Giải thích rõ hơn"): Sử dụng thông tin từ mục **[PHẦN GIẢI THÍCH]**.
    3. Nâng cao (Khi HS hỏi về kiến thức khó, mở rộng): Sử dụng thông tin từ mục **[PHẦN NÂNG CAO]**.

    C. NGÔN NGỮ & ĐỊNH DẠNG (Bắt buộc):
    1. Danh pháp: Sử dụng danh pháp mới (acid, base, oxide, oxygen, hydrogen...).
    2. # CẬP NHẬT QUY TẮC THỂ TÍCH KHÍ CHI TIẾT
        "3. QUY TẮC THỂ TÍCH KHÍ (PHÂN BIỆT CHUẨN & TIÊU CHUẨN): \n"
        "   - ĐIỀU KIỆN CHUẨN: Nếu đề bài ghi 'điều kiện chuẩn' hoặc viết tắt là '(đkc)', "
        "BẮT BUỘC sử dụng công thức $V = n \cdot 24,79$ (theo chương trình GDPT 2018).\n"
        "   - ĐIỀU KIỆN TIÊU CHUẨN: Chỉ khi đề bài ghi rõ 'điều kiện tiêu chuẩn' hoặc viết tắt là '(đktc)', "
        "mới sử dụng công thức $V = n \cdot 22,4$.\n"
        "   - MẶC ĐỊNH: Nếu đề bài không ghi gì thêm, hãy ưu tiên sử dụng điều kiện chuẩn $24,79$ và ghi chú rõ cho học sinh.\n"
    3. Hiển thị: Luôn dùng LaTeX ($$...$$) cho công thức và phương trình. Hệ phương trình phải nằm trong một khối `\begin{cases}` duy nhất.

    D. QUY TẮC TƯƠNG TÁC BÀI TẬP (RÈN LUYỆN KỸ NĂNG):
    1. QUY TẮC "DỪNG LẠI": Khi nhận được yêu cầu giải bài tập (có số liệu/tính toán), DÙ HỌC SINH CÓ YÊU CẦU "GIẢI CHI TIẾT" NGAY, bạn vẫn KHÔNG ĐƯỢC giải ngay lập tức.
    2. PHẢN HỒI GIA SƯ: Bạn phải chào và khuyên nhủ học sinh như sau: 
   "Thầy đã nhận được bài tập của em. Để giúp em nâng cao kỹ năng tư duy và nhớ lâu cách làm, thầy khuyên em nên chọn cách thầy 'hướng dẫn từng bước' để em tự giải. Việc tự mình vượt qua bài tập sẽ giúp em tiến bộ rất nhanh đấy! 
   Tuy nhiên, nếu em thực sự đang cần bài giải chi tiết ngay, thầy vẫn sẽ hỗ trợ. Vậy em muốn thầy hướng dẫn tư duy hay đưa bài giải chi tiết luôn?"
    3. THỰC HIỆN GIẢI:
   - Nếu HS khẳng định lại là "muốn giải chi tiết": Áp dụng chính sách HYBRID 3 cấp độ để đưa ra lời giải hoàn chỉnh.
   - Nếu HS chọn "hướng dẫn từng bước": Đưa ra gợi ý bước 1 (thường là tính số mol hoặc viết PTHH) và đợi HS phản hồi.

    E. CHÍNH SÁCH HYBRID 3 CẤP ĐỘ (Khi giải bài):
    - Cấp 1: Nếu có sẵn trong [BÀI TẬP VÀ GIẢI CHI TIẾT], dùng lời giải đó.
    - Cấp 2 (Hybrid Logic): Nếu bài mới nhưng lý thuyết có trong tài liệu, dùng trí thông minh logic để giải dựa trên lý thuyết đó.
    - Cấp 3 (Từ chối): Nếu lý thuyết cơ bản không có trong tài liệu, từ chối theo quy tắc A.2.
    """)

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.1)
        )
        
        # Nạp tài liệu lần đầu
        list_parts = [types.Part.from_uri(file_uri=f"https://generativelanguage.googleapis.com/v1beta/{f}", mime_type="text/plain") for f in LIST_FILES]
        list_parts.append(types.Part.from_text(text="Hãy học thuộc tài liệu này. Nếu câu hỏi không có trong đây, trả lời có kèm mã [MISSING_DOC]."))
        chat.send_message(list_parts)
        return client, chat
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return None, None

client, chat_session = setup_chat_session()

# ==================================================
# 🤖 XỬ LÝ GIAO DIỆN CHAT
# ==================================================
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

prompt = st.chat_input("Nhập câu hỏi cho thầy...")
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"])

if prompt:
    if not client: st.stop()
    
    cleaned_prompt = prompt.strip()
    message_parts = []
    
    # Xử lý ảnh nếu có
    if uploaded_file:
        image_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type)
        message_parts.append(image_part)
        display_user_msg = f"📝 (Kèm ảnh) {cleaned_prompt}"
    else:
        display_user_msg = cleaned_prompt

    # Lưu và hiển thị câu hỏi của User
    st.session_state.messages.append({"role": "user", "content": display_user_msg})
    save_chat_history(st.session_state.messages)
    
    with chat_container:
        with st.chat_message("user"):
            st.markdown(display_user_msg)

    # Phản hồi của Assistant
    with st.chat_message("assistant"):
        with st.spinner("Thầy đang suy nghĩ..."):
            try:
                message_parts.append(types.Part.from_text(text=cleaned_prompt))
                response = chat_session.send_message(message_parts)
                res_text = response.text.strip()
                
                # Kiểm tra lỗi thiếu tài liệu
                if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                    # Đọc file -> Thêm mới -> Lưu (để không mất dữ liệu cũ)
                    current_missing = load_missing_questions()
                    if cleaned_prompt not in current_missing:
                        current_missing.append(f"{datetime.now().strftime('%d/%m')} - {cleaned_prompt}")
                        save_missing_questions(current_missing)
                        st.session_state.missing_questions = current_missing
                    
                    final_res = ERROR_MESSAGE
                else:
                    final_res = res_text

                st.markdown(final_res)
                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_chat_history(st.session_state.messages) # Lưu lại ngay lập tức
                
            except Exception as e:
                st.error(f"Lỗi kết nối: {e}")
