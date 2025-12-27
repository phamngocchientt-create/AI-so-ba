import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 

# ==================================================
# 📌 BƯỚC 1: DANH SÁCH FILE ID (Giữ nguyên)
# ==================================================
LIST_FILES = ['files/a5emhz9lf124', 'files/wg9rux3tpeja'] 
# ==================================================

STORAGE_FILE = "missing_questions.json"
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 

HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

# --- CÁC HÀM XỬ LÝ JSON (Giữ nguyên) ---
def load_missing_questions():
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                return json.loads(content) if content else []
        return []
    except Exception as e:
        return []

def save_missing_questions(questions_list):
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(questions_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

def clear_missing_questions():
    st.session_state.missing_questions = []
    save_missing_questions(st.session_state.missing_questions)

# ==================================================
# KHỞI TẠO ỨNG DỤNG STREAMLIT
# ==================================================
st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_missing_questions()

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    st.info("🤖 Model: gemini-1.5-flash")
    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung Tài liệu")
    
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
        
        st.subheader("⚠️ Quản lý Dữ liệu")
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            submitted = st.form_submit_button("Xóa Toàn bộ")
            if submitted:
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    clear_missing_questions()
                    st.success("✅ Đã xóa!")
                    st.rerun()
                else:
                    st.error("❌ Sai mật khẩu.")
    else:
        st.write("Không có câu hỏi nào cần bổ sung.")

@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Thiếu API Key.")
        return None, None 

    client = genai.Client(api_key=api_key)

    # GIỮ NGUYÊN TOÀN BỘ VĂN BẢN CỦA BẠN - CHỈ THÊM YÊU CẦU MÃ LỖI Ở MỤC A.2
    sys_instruct = (r"""
        Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.
        
   [QUY TẮC HIỂN THỊ - CHỐNG DÍNH CHỮ]:
        1. Mỗi phương trình hóa học PHẢI nằm trong khối LaTeX riêng biệt: $$ phương trình $$.
        2. Sau mỗi khối $$...$$ hoặc mỗi đoạn văn, BẮT BUỘC xuống dòng 2 lần.
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
            config=types.GenerateContentConfig(system_instruction=sys_instruct, temperature=0.3)
        )
        
        list_parts = []
        for file_id in LIST_FILES:
            uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_id}"
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain"))
        
        initial_prompt = "Hãy đọc kỹ tài liệu và sẵn sàng sửa lỗi định dạng phân số/công thức từ PDF để hỗ trợ học sinh."
        list_parts.append(types.Part.from_text(text=initial_prompt)) 
        chat.send_message(list_parts)
        return client, chat
    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
        return None, None

# ==================================================
# 🤖 GIAO DIỆN VÀ XỬ LÝ TIN NHẮN
# ==================================================
client, chat_session = setup_chat_session() 

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]

chat_container = st.container()

st.markdown("---")
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh đề bài tại đây", type=["jpg", "jpeg", "png"], key="fixed_bottom_uploader")

prompt = st.chat_input("Nhập câu hỏi cho thầy...")

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    user_question_for_history = cleaned_prompt
    message_parts = []
    
    if uploaded_file is not None:
        try:
            image_bytes = uploaded_file.getvalue()
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=uploaded_file.type)
            message_parts.append(image_part)
            user_question_for_history = f"📝 (Có ảnh kèm theo) {cleaned_prompt}"
        except Exception as e:
            st.error(f"❌ Lỗi ảnh: {e}")
            st.stop()
    
    st.session_state.messages.append({"role": "user", "content": user_question_for_history})

    with chat_container:
        with st.chat_message("user"):
            if uploaded_file is not None:
                st.image(uploaded_file, width=300)
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thầy đang xem bài..."):
                try:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
                    response = chat_session.send_message(message_parts)
                    res_text = response.text
                    
                    # ✅ CÁCH SỬA MỚI: Không dùng .replace("\n", "\n\n") nữa
                    # Chỉ làm sạch các khoảng trắng thừa ở đầu/cuối
                    display_text = res_text.strip()

                    if ERROR_MESSAGE_TAG.upper() in display_text.upper():
                        if user_question_for_history not in st.session_state.missing_questions:
                            st.session_state.missing_questions.append(user_question_for_history)
                            save_missing_questions(st.session_state.missing_questions)
                        
                        clean_res = display_text.replace(ERROR_MESSAGE_TAG, "").strip()
                        st.markdown(clean_res)
                        st.session_state.messages.append({"role": "assistant", "content": clean_res})
                        st.rerun() 
                    else:
                        # Hiển thị trực tiếp, Streamlit sẽ tự xử lý Markdown
                        st.markdown(display_text)
                        st.session_state.messages.append({"role": "assistant", "content": display_text})
                        
                except Exception as e:
                    st.error(f"Lỗi: {e}")










