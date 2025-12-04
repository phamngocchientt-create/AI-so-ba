import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 

# ==================================================
# 📌 BƯỚC 1: DÁN DANH SÁCH FILE ID CỦA BẠN VÀO ĐÂY
# ==================================================
# Dùng list file hiện tại của bạn (Giữ nguyên)
LIST_FILES = ['files/oq5xngmykfrg', 'files/qkiv48ec8tms'] 
# LƯU Ý: Nếu LIST_FILES bạn dùng là 3 file PDF, bạn cần cập nhật lại chính xác.
# Tôi dùng danh sách bạn cung cấp gần nhất
# ==================================================

# Định nghĩa tệp lưu trữ và thông báo lỗi cố định
STORAGE_FILE = "missing_questions.json"
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 

# ✅ FIX CÂU CHÀO: Định nghĩa câu chào chính xác để hardcode
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

# ==================================================
# CÁC HÀM XỬ LÝ LƯU TRỮ DỮ LIỆU BỀN VỮNG (JSON)
# ==================================================

def load_missing_questions():
    """Tải danh sách câu hỏi cần bổ sung từ tệp JSON."""
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                return json.loads(content) if content else []
        return []
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu từ {STORAGE_FILE}. Trả về danh sách rỗng: {e}")
        return []

def save_missing_questions(questions_list):
    """Lưu danh sách câu hỏi cần bổ sung vào tệp JSON."""
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(questions_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi khi lưu dữ liệu vào {STORAGE_FILE}: {e}")

# ==================================================
# HÀM XỬ LÝ XÓA DANH SÁCH (Được gọi sau khi xác thực)
# ==================================================
def clear_missing_questions():
    """Xóa danh sách trong session state và lưu trạng thái rỗng vào JSON."""
    st.session_state.missing_questions = []
    save_missing_questions(st.session_state.missing_questions)
    

# ==================================================
# KHỞI TẠO ỨNG DỤNG STREAMLIT
# ==================================================

st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

# Khởi tạo session state bằng cách tải từ file
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_missing_questions()

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    st.info("🤖 Model: gemini-2.0-flash")
    
    # ----------------------------------------------------
    # HIỂN THỊ CÂU HỎI CẦN BỔ SUNG TÀI LIỆU
    # ----------------------------------------------------
    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung Tài liệu")
    
    if st.session_state.missing_questions:
        # Hiển thị các câu hỏi
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
            
        # ------------------------------------------------------------------
        # 🔒 PHẦN MỚI: FORM NHẬP MẬT KHẨU ĐỂ XÓA DANH SÁCH
        # ------------------------------------------------------------------
        st.subheader("⚠️ Quản lý Dữ liệu (Yêu cầu Mật khẩu)")
        
        with st.form("clear_form"):
            password = st.text_input("Nhập Mật khẩu quản trị để xóa", type="password")
            submitted = st.form_submit_button("Xóa Toàn bộ Câu hỏi Đã Ghi nhận")
            
            if submitted:
                required_password = st.secrets.get(PASSWORD_KEY, "admin123") 
                
                if password == required_password:
                    clear_missing_questions() # Xóa và lưu vào JSON
                    st.success("✅ Đã xóa danh sách thành công! Dữ liệu đã được làm sạch.")
                    st.rerun() # Tải lại ứng dụng để cập nhật hiển thị
                else:
                    st.error("❌ Mật khẩu không chính xác. Không thể xóa danh sách.")
        # ------------------------------------------------------------------
    else:
        st.write("Không có câu hỏi nào cần bổ sung tài liệu.")
        
    st.markdown("---")
    
    with st.expander("Hướng dẫn phân tầng kiến thức"):
        st.write("- Hỏi lý thuyết thông thường: Trả lời từ **[KIẾN THỨC CƠ BẢN]**.")
        st.write("- Hỏi 'Tại sao/Vì sao/Giải thích': Trả lời từ **[PHẦN GIẢI THÍCH]**.")
        st.write("- Hỏi 'Nâng cao/Đặc biệt': Trả lời từ **[PHẦN NÂNG CAO]**.")
        st.write("- Hỏi 'Giải chi tiết/Bài tập': Trả lời từ **[BÀI TẬP VÀ GIẢI CHI TIẾT]**.")


@st.cache_resource
def setup_chat_session():
    """Thiết lập phiên chat và tải file, truyền System Instruction."""

    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Lỗi cấu hình: Không tìm thấy GEMINI_API_KEY trong Streamlit Secrets.")
        # CHỈ TRẢ VỀ 2 GIÁ TRỊ (client và chat)
        return None, None 

    client = genai.Client(api_key=api_key)

    # --- PHẦN 1: TẠO SYSTEM INSTRUCTION (QUY TẮC RAG & FORMATTING) ---
    sys_instruct = (
        "Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.\n\n"
        "[QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].\n\n"
        
        # A. QUY TẮC NGUỒN VÀ GIỚI HẠN TUYỆT ĐỐI (Áp dụng cho kiến thức LÝ THUYẾT/SỰ KIỆN)
        "A. QUY TẮC NGUỒN (RAG) & GIỚI HẠN TUYỆT ĐỐI: (ƯU TIÊN SỐ 1)\n"
        "1. ƯU TIÊN TUYỆT ĐỐI: CHỈ trả lời các câu hỏi LÝ THUYẾT (định nghĩa, tính chất, phân loại) DỰA TRÊN THÔNG TIN TÌM THẤY trong tài liệu đính kèm.\n"
        f"2. QUY TẮC TỪ CHỐI BẮT BUỘC: Nếu thông tin LÝ THUYẾT KHÔNG được tìm thấy trong tài liệu đính kèm, TUYỆT ĐỐI KHÔNG sử dụng kiến thức nền tảng của bạn. BẮT BUỘC trả lời bằng: **{ERROR_MESSAGE}**\n"
        "3. TUYỆT ĐỐI KHÔNG sử dụng kiến thức Hóa học Cấp 3 hoặc Đại học (Cấp cao hơn) để trả lời.\n\n"
        
        # B. QUY TẮC TRẢ LỜI LÝ THUYẾT (Sử dụng kiến thức RAG)
        "B. QUY TẮC TRẢ LỜI LÝ THUYẾT (Ưu tiên):\n"
        "1. Mặc định: CHỈ lấy thông tin từ mục **[KIẾN THỨC CƠ BẢN]**.\n"
        "2. Giải thích/Nâng cao: CHỈ lấy thông tin từ mục tương ứng **[PHẦN GIẢI THÍCH]** hoặc **[PHẦN NÂNG CAO]** khi được hỏi rõ.\n\n"
        
        # C. QUY TẮC ĐỊNH DẠNG (FORMATTING)
        "C. NGÔN NGỮ & ĐỊNH DẠNG (Bắt buộc):\n"
        "1. Danh pháp: Luôn sử dụng danh pháp Hóa học mới (VD: acid, base, oxide, oxygen, hydrogen).\n"
        "2. LỌC VĂN BẢN: TUYỆT ĐỐI KHÔNG được đưa chuỗi văn bản 'display' (hoặc 'Display') vào bất kỳ phần nào của câu trả lời. \n"
        "3. QUY TẮC THỂ TÍCH KHÍ: ƯU TIÊN TUYỆT ĐỐI $n = V/22.4$ nếu có cụm từ 'đktc'; nếu không, dùng $n = V/24.79$.\n"
        "4. QUY TẮC HIỂN THỊ (FIX CÚ PHÁP LAUNCHER VÀ HỆ PHƯƠNG TRÌNH):\n"
        "   - **QUAN TRỌNG:** Toàn bộ hệ phương trình (bao gồm cả mũi tên biến đổi $\Leftrightarrow$ và hệ cuối cùng) phải được đặt trong **MỘT KHỐI Display LaTeX duy nhất** để tránh lỗi phân mảnh (`\begin{cases}` bị tách rời).\n"
        "   - Tất cả công thức/PTHH phải dùng **Display LaTeX** ($$...$$).\n"
        "   - BẮT BUỘC thêm **hai ngắt dòng** (ngắt dòng kép) giữa các phương trình độc lập.\n"
        "   - **TUYỆT ĐỐI KHÔNG** sử dụng các lệnh phức tạp như `\\text{ }` để tạo khoảng trống, thay vào đó, hãy sử dụng cú pháp LaTeX cơ bản nhất.\n"
        "   - **QUAN TRỌNG VỀ HỆ PHƯƠNG TRÌNH:** Sau khi liệt kê các phương trình của hệ (1) và (2) bằng Display LaTeX:\n"
        "     - **TUYỆT ĐỐI BỎ QUA** các bước tính toán giải hệ phương trình.\n"
        "     - TRỰC TIẾP đưa **kết quả cuối cùng của các biến số** (ví dụ: 'Giải hệ, ta được x = 0.1 mol và y = 0.2 mol.') dưới dạng **VĂN BẢN THUẦN TÚY** (Không dùng LaTeX) và tiếp tục bài giải.\n\n"
        "5. QUY TẮC CẤU TRÚC HÓA HỌC: Khi mô tả cấu trúc phức tạp (mạch vòng, mạch nhánh), TUYỆT ĐỐI KHÔNG SỬ DỤNG các lệnh vẽ hình học (như \\begin{array}, \\diagdown). Ưu tiên sử dụng Danh pháp IUPAC, Công thức phân tử và Ký hiệu SMILES (Ví dụ: Cyclohexane có SMILES là C1CCCCC1) để đảm bảo tính chính xác và dễ đọc.\n\n"
        
        # D. QUY TẮC TRẢ LỜI BÀI TẬP (Áp dụng Trí tuệ Logic)
        "D. QUY TẮC TRẢ LỜI BÀI TẬP (Có số liệu/yêu cầu tính toán):\n"
        "   - SỬ DỤNG TRÍ THÔNG MINH LOGIC VÀ TOÁN HỌC của bạn để tính toán và giải quyết các bài toán Hóa học.\n"
        "   - **CHÍNH SÁCH HYBRID:** Nếu câu hỏi LÀ bài tập tính toán, bạn được phép sử dụng trí thông minh giải quyết vấn đề ngay cả khi dạng bài tập đó không có trong thư viện, **miễn là lý thuyết cơ bản (công thức, PTHH) của bài toán đó ĐÃ được tìm thấy trong tài liệu đính kèm.**\n"
        "   - LUÔN hỏi học sinh: 'Em muốn được hướng dẫn từng bước hay giải chi tiết?'\n"
        "   - Trình bày lời giải chi tiết theo các bước logic và chuyên nghiệp."
    )
    
    # --- PHẦN 2: KHỞI TẠO CHAT SESSION (Config) ---
    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.3
            )
        )
        
        # --- PHẦN 3: GỬI FILE ID và YÊU CẦU XÁC NHẬN (Trong Tin nhắn đầu tiên) ---
        list_parts = []
        for file_name in LIST_FILES:
            uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
            # LƯU Ý: Đã sửa lại để dùng file list cuối cùng
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="application/pdf")) 
        
        # SỬ DỤNG MINIMAL PROMPT để thiết lập RAG Context (AI chỉ cần xác nhận, không cần chào)
        initial_prompt_to_ai = "Hãy đọc kỹ tài liệu và tuân thủ nghiêm ngặt mọi quy tắc, đặc biệt là Quy tắc A."
        list_parts.append(types.Part.from_text(text=initial_prompt_to_ai)) 

        # Gửi file ID trong tin nhắn đầu tiên của phiên chat để tạo ngữ cảnh
        chat.send_message(list_parts)
        
        # CHỈ TRẢ VỀ client và chat, loại bỏ phản hồi của AI
        return client, chat
        
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo phiên chat. Vui lòng kiểm tra File ID ({LIST_FILES}) và API Key: {e}")
        # CHỈ TRẢ VỀ 2 GIÁ TRỊ (client và chat)
        return None, None


# --- KHỞI TẠO PHIÊN CHAT VÀ GIAO DIỆN CHÍNH ---
# ✅ FIX: CHỈ NHẬN 2 GIÁ TRỊ TỪ HÀM SETUP
client, chat_session = setup_chat_session() 

if "messages" not in st.session_state:
    # ✅ FIX: LUÔN DÙNG CÂU CHÀO HARDCODE
    st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
else:
    # Nếu session đã tồn tại, không làm gì
    pass
    
# ... (Phần code còn lại giữ nguyên) ...

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# WIDGET TẢI FILE ẢNH
uploaded_file = st.file_uploader(
    "🖼️ Tải ảnh câu hỏi (tùy chọn)", 
    type=["jpg", "jpeg", "png"],
    key="image_uploader_widget"
)


if prompt := st.chat_input("Nhập câu hỏi..."):
    if not client:
        st.stop()

    cleaned_prompt = prompt.strip()
    user_question_for_history = cleaned_prompt
    
    # --- 1. CHUẨN BỊ TIN NHẮN (GỒM VĂN BẢN VÀ ẢNH) ---
    message_parts = []
    
    # 1a. Thêm file ảnh (nếu có)
    if uploaded_file is not None:
        try:
            image_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"] else "image/jpeg"
            
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type 
            )
            message_parts.append(image_part)
            
            user_question_for_history = f"📝 Câu hỏi (kèm ảnh: {uploaded_file.name}): {cleaned_prompt}"
            
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file ảnh: {e}. Vui lòng thử lại với file ảnh khác.")
            st.stop()
    
    st.session_state.messages.append({"role": "user", "content": user_question_for_history})

    # 1b. Thêm văn bản câu hỏi (Phải là phần tử cuối cùng)
    if cleaned_prompt:
        message_parts.append(types.Part.from_text(text=cleaned_prompt))
    else:
        message_parts.append(types.Part.from_text(text="Phân tích hình ảnh này."))


    # --- 2. HIỂN THỊ TIN NHẮN NGƯỜI DÙNG ---
    with st.chat_message("user"):
        if uploaded_file is not None:
            st.image(uploaded_file, caption=f"Ảnh câu hỏi đã tải lên: {uploaded_file.name}")
        st.markdown(cleaned_prompt)


    # --- 3. GỬI VÀ NHẬN PHẢN HỒI ---
    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích ảnh và cấp độ câu hỏi..."):
            try:
                response = chat_session.send_message(message_parts)
                response_text = response.text
                
                # KIỂM TRA PHẢN HỒI VÀ LƯU CÂU HỎI KHÔNG TRẢ LỜI ĐƯỢC
                if ERROR_MESSAGE_TAG in response_text:
                    display_text = response_text.replace(ERROR_MESSAGE_TAG, "").strip()
                    
                    if cleaned_prompt and cleaned_prompt != "Phân tích hình ảnh này.":
                        question_to_save = cleaned_prompt
                    elif uploaded_file is not None:
                        question_to_save = f"(Ảnh: {uploaded_file.name}) + {cleaned_prompt}"
                    else:
                        question_to_save = cleaned_prompt
                        
                    if question_to_save not in st.session_state.missing_questions:
                        st.session_state.missing_questions.append(question_to_save)
                        # GỌI HÀM LƯU DỮ LIỆU BỀN VỮNG
                        save_missing_questions(st.session_state.missing_questions)
                        
                    st.markdown(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    
                else:
                    # Trả lời bình thường
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
            except Exception as e:
                st.error(f"Lỗi: {e}")



