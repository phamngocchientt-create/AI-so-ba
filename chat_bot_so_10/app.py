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
LIST_FILES = ['files/02x7nnbn4stv', 'files/itbrahjupfp2'] 
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
        return None, None 

    client = genai.Client(api_key=api_key)

    # --- PHẦN 1: TẠO SYSTEM INSTRUCTION (QUY TẮC RAG & FORMATTING) ---
    # ✅ FIX: Sử dụng Raw String (r""") để loại bỏ SyntaxWarning và đảm bảo ký tự '\' chính xác.
    sys_instruct = (r"""
        Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.

        [QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].

        # A. QUY TẮC NGUỒN VÀ GIỚI HẠN TUYỆT ĐỐI (Áp dụng cho kiến thức LÝ THUYẾT/SỰ KIỆN)
        A. QUY TẮC NGUỒN (RAG) & GIỚI HẠN TUYỆT ĐỐI: (ƯU TIÊN SỐ 1)
        1. ƯU TIÊN TUYỆT ĐỐI: CHỈ trả lời các câu hỏi LÝ THUYẾT (định nghĩa, tính chất, phân loại) DỰA TRÊN THÔNG TIN TÌM THẤY trong tài liệu đính kèm.
        2. QUY TẮC TỪ CHỐI BẮT BUỘC: Nếu thông tin LÝ THUYẾT KHÔNG được tìm thấy trong tài liệu đính kèm, TUYỆT ĐỐI KHÔNG sử dụng kiến thức nền tảng của bạn. BẮT BUỘC trả lời bằng: **{ERROR_MESSAGE}**
        3. TUYỆT ĐỐI KHÔNG sử dụng kiến thức Hóa học Cấp 3 hoặc Đại học (Cấp cao hơn) để trả lời.

        # B. QUY TẮC TRẢ LỜI LÝ THUYẾT (Sử dụng kiến thức RAG)
        B. QUY TẮC TRẢ LỜI LÝ THUYẾT (Ưu tiên):
        1. Mặc định: CHỈ lấy thông tin từ mục **[KIẾN THỨC CƠ BẢN]**.
        2. Giải thích/Nâng cao: CHỈ lấy thông tin từ mục tương ứng **[PHẦN GIẢI THÍCH]** hoặc **[PHẦN NÂNG CAO]** khi được hỏi rõ.

        # C. QUY TẮC ĐỊNH DẠNG (FORMATTING)
        C. NGÔN NGỮ & ĐỊNH DẠNG (Bắt buộc):
        1. Danh pháp: Luôn sử dụng danh pháp Hóa học mới (VD: acid, base, oxide, oxygen, hydrogen).
        2. LỌC VĂN BẢN: TUYỆT ĐỐI KHÔNG được đưa chuỗi văn bản 'display' (hoặc 'Display') vào bất kỳ phần nào của câu trả lời. 
        
        # ✅ FIX: QUY TẮC THỂ TÍCH KHÍ ĐÃ ĐƯỢC TĂNG CƯỜNG
        3. QUY TẮC THỂ TÍCH KHÍ (CTPT 2018): 
           - NGUYÊN TẮC TUYỆT ĐỐI: CHỈ sử dụng $V = n \cdot 22.4$ nếu đề bài ghi rõ **'điều kiện tiêu chuẩn'** (đktc).
           - MẶC ĐỊNH SỬ DỤNG: Trong mọi trường hợp khác (như **'điều kiện chuẩn'** (đkc), hoặc không ghi rõ), **BẮT BUỘC** sử dụng công thức $V = n \cdot 24.79$ (L/mol) theo Chương trình Phổ thông 2018.

        4. QUY TẮC HIỂN THỊ (FIX CÚ PHÁP LAUNCHER VÀ HỆ PHƯƠNG TRÌNH):
           - **QUAN TRỌNG:** Toàn bộ hệ phương trình (bao gồm cả mũi tên biến đổi $\Leftrightarrow$ và hệ cuối cùng) phải được đặt trong **MỘT KHỐI Display LaTeX duy nhất** để tránh lỗi phân mảnh (`\begin{cases}` bị tách rời).
           - Tất cả công thức/PTHH phải dùng **Display LaTeX** ($$...$$).
           - BẮT BUỘC thêm **hai ngắt dòng** (ngắt dòng kép) giữa các phương trình độc lập.
           - **TUYỆT ĐỐI KHÔNG** sử dụng các lệnh phức tạp như `\text{ }` để tạo khoảng trống, thay vào đó, hãy sử dụng cú pháp LaTeX cơ bản nhất.
           - **QUAN TRỌNG VỀ HỆ PHƯƠNG TRÌNH:** Sau khi liệt kê các phương trình của hệ (1) và (2) bằng Display LaTeX:
             - **TUYỆT ĐỐI BỎ QUA** các bước tính toán giải hệ phương trình.
             - TRỰC TIẾP đưa **kết quả cuối cùng của các biến số** (ví dụ: 'Giải hệ, ta được x = 0.1 mol và y = 0.2 mol.') dưới dạng **VĂN BẢN THUẦN TÚY** (Không dùng LaTeX) và tiếp tục bài giải.

           5. QUY TẮC CẤU TRÚC HÓA HỌC: Khi mô tả cấu trúc phức tạp (mạch vòng, mạch nhánh), TUYỆT ĐỐI KHÔNG SỬ DỤNG các lệnh vẽ hình học (như \begin{array}, \diagdown). Ưu tiên sử dụng Danh pháp IUPAC, Công thức phân tử và Ký hiệu SMILES (Ví dụ: Cyclohexane có SMILES là C1CCCCC1) để đảm bảo tính chính xác và dễ đọc.

        # D. QUY TẮC TRẢ LỜI BÀI TẬP (Áp dụng Trí tuệ Logic theo 3 cấp độ)
        D. QUY TẮC TRẢ LỜI BÀI TẬP (Có số liệu/yêu cầu tính toán - CHÍNH SÁCH HYBRID 3 CẤP):
           - SỬ DỤNG TRÍ THÔNG MINH LOGIC VÀ TOÁN HỌC của bạn để tính toán và giải quyết các bài toán Hóa học.
           - **CHÍNH SÁCH HYBRID:** Nếu câu hỏi LÀ bài tập tính toán, bạn được phép sử dụng trí thông minh giải quyết vấn đề ngay cả khi dạng bài tập đó không có trong thư viện, **miễn là lý thuyết cơ bản (công thức, PTHH) của bài toán đó ĐÃ được tìm thấy trong tài liệu đính kèm.**
           - **1. ƯU TIÊN TUYỆT ĐỐI (Dạng Đã có Sẵn):** Nếu bài tập TÌM THẤY GIỐNG HỆT trong mục **[BÀI TẬP VÀ GIẢI CHI TIẾT]**, phải đưa ra lời giải đó (không dùng trí thông minh giải lại).\n"
           - **2. HYBRID LOGIC (Dạng Mới/Lý thuyết có sẵn):** Nếu bài tập KHÔNG GIỐNG HỆT nhưng có dạng tương tự hoặc lý thuyết cơ bản (công thức, PTHH) của bài toán đó ĐÃ được tìm thấy trong mục **[KIẾN THỨC CƠ BẢN]**, HÃY SỬ DỤNG TRÍ THÔNG MINH LOGIC VÀ TOÁN HỌC của bạn để tính toán và giải quyết bài toán đó.
           - **3. TỪ CHỐI (Không có Cơ sở Lý thuyết):** Nếu bài tập là DẠNG HOÀN TOÀN MỚI và lý thuyết cơ bản (công thức, PTHH) KHÔNG CÓ trong tài liệu đính kèm, phải từ chối theo Quy tắc A.2 (TỪ CHỐI BẮT BUỘC).
           - LUÔN hỏi học sinh: 'Em muốn được hướng dẫn từng bước hay giải chi tiết?'
           - Trình bày lời giải chi tiết theo các bước logic và chuyên nghiệp.
    """)

    # --- PHẦN 2: KHỞI TẠO CHAT SESSION (Config) ---
    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct.format(ERROR_MESSAGE=ERROR_MESSAGE),
                temperature=0.3
            )
        )
        
        # --- PHẦN 3: GỬI FILE ID và YÊU CẦU XÁC NHẬN (Trong Tin nhắn đầu tiên) ---
        list_parts = []
        for file_name in LIST_FILES:
            uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
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
        return None, None
