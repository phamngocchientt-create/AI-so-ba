import streamlit as st
from google import genai
from google.genai import types
import os
import io

# ==================================================
# 📌 BƯỚC 1: DÁN DANH SÁCH FILE ID CỦA BẠN VÀO ĐÂY
# ==================================================
LIST_FILES = ['files/tgd5y7hlkwo9', 'files/ldto0s443gu2']
# ==================================================

st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

# Định nghĩa thông báo lỗi cố định để dễ dàng nhận dạng (Unique Tag)
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"

# Khởi tạo session state cho các câu hỏi cần bổ sung
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = []

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    st.info("🤖 Model: gemini-2.0-flash")
    
    # ----------------------------------------------------
    # 🆕 PHẦN MỚI: HIỂN THỊ CÂU HỎI CẦN BỔ SUNG
    # ----------------------------------------------------
    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung Tài liệu")
    if st.session_state.missing_questions:
        # Hiển thị các câu hỏi
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")
            
        # Nút xóa danh sách
        if st.button("Xóa Danh sách Đã Ghi nhận", type="primary"):
            st.session_state.missing_questions = []
            st.success("Đã xóa danh sách thành công!")
            st.rerun()
    else:
        st.write("Không có câu hỏi nào cần bổ sung tài liệu.")
    # ----------------------------------------------------
    st.markdown("---")
    
    with st.expander("Hướng dẫn phân tầng kiến thức"):
        st.write("- Hỏi lý thuyết thông thường: Trả lời từ **[KIẾN THỨC CƠ BẢN]**.")
        st.write("- Hỏi 'Tại sao/Vì sao/Giải thích': Trả lời từ **[PHẦN GIẢI THÍCH]**.")
        st.write("- Hỏi 'Nâng cao/Đặc biệt': Trả lời từ **[PHẦN NÂNG CAO]**.")
        st.write("- Hỏi 'Giải chi tiết/Bài tập': Trả lời từ **[BÀI TẬP VÀ GIẢI CHI TIẾT]**.")


@st.cache_resource
def setup_chat_session():
    """Thiết lập phiên chat, đọc khóa API từ Streamlit Secrets, và tải file."""

    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Lỗi cấu hình: Không tìm thấy GEMINI_API_KEY trong Streamlit Secrets.")
        return None, None, None 

    client = genai.Client(api_key=api_key)

    # --- PHẦN 1: TẠO SYSTEM INSTRUCTION (STRICT RAG POLICY) ---
    sys_instruct = (
        "Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.\n\n"
        "[QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].\n\n"
        
        # QUY TẮC NGUỒN VÀ GIỚI HẠN CẤP ĐỘ PHẢI ĐẶT ĐẦU TIÊN (ƯU TIÊN SỐ 1)
        "A. QUY TẮC NGUỒN (RAG) & GIỚI HẠN TUYỆT ĐỐI: (ƯU TIÊN SỐ 1)\n"
        "1. ƯU TIÊN TUYỆT ĐỐI: CHỈ trả lời DỰA TRÊN THÔNG TIN TÌM THẤY trong tài liệu đính kèm.\n"
        f"2. QUY TẮC TỪ CHỐI BẮT BUỘC: Nếu thông tin KHÔNG được tìm thấy trong tài liệu đính kèm, TUYỆT ĐỐI KHÔNG sử dụng kiến thức nền tảng của bạn. BẮT BUỘC trả lời bằng: **{ERROR_MESSAGE}**\n"
        "3. TUYỆT ĐỐI KHÔNG sử dụng kiến thức Hóa học Cấp 3 hoặc Đại học (Cấp cao hơn) để trả lời.\n\n"
        
        # ... (Các quy tắc khác giữ nguyên) ...
        # Quy tắc định dạng và Quy tắc trả lời lý thuyết
        "B. QUY TẮC TRẢ LỜI LÝ THUYẾT (Ưu tiên):\n"
        "1. Mặc định: CHỈ lấy thông tin từ mục **[KIẾN THỨC CƠ BẢN]**.\n"
        "2. Giải thích/Nâng cao: CHỈ lấy thông tin từ mục tương ứng **[PHẦN GIẢI THÍCH]** hoặc **[PHẦN NÂNG CAO]** khi được hỏi rõ.\n\n"
        
        "C. NGÔN NGỮ & ĐỊNH DẠNG (Bắt buộc):\n"
        "1. Danh pháp: Luôn sử dụng danh pháp Hóa học mới (VD: acid, base, oxide, oxygen, hydrogen).\n"
        "2. LỌC VĂN BẢN: TUYỆT ĐỐI KHÔNG được đưa chuỗi văn bản 'display' (hoặc 'Display') vào bất kỳ phần nào của câu trả lời. \n"
        "3. QUY TẮC THỂ TÍCH KHÍ: ƯU TIÊN TUYỆT ĐỐI $n = V/22.4$ nếu có cụm từ 'đktc'; nếu không, dùng $n = V/24.79$.\n"
        "4. QUY TẮC HIỂN THỊ (FIX CÚ PHÁP LAUNCHER):\n"
        "  - Tất cả công thức/PTHH phải dùng **Display LaTeX** ($$...$$).\n"
        "  - BẮT BUỘT thêm **hai ngắt dòng** (ngắt dòng kép) giữa các phương trình liên tiếp.\n"
        "  - **TUYỆT ĐỐI KHÔNG** sử dụng các lệnh phức tạp như `\\text{ }` để tạo khoảng trống, thay vào đó, hãy sử dụng cú pháp LaTeX cơ bản nhất.\n"
        "  - **QUAN TRỌNG VỀ HỆ PHƯƠNG TRÌNH:** Sau khi liệt kê các phương trình của hệ (1) và (2) bằng Display LaTeX:\n"
        "    - **TUYỆT ĐỐI BỎ QUA** các bước tính toán giải hệ phương trình.\n"
        "    - TRỰC TIẾP đưa **kết quả cuối cùng của các biến số** (ví dụ: 'Giải hệ, ta được x = 0.1 mol và y = 0.2 mol.') dưới dạng **VĂN BẢN THUẦN TÚY** (Không dùng LaTeX) và tiếp tục bài giải.\n\n"
        "5. QUY TẮC CẤU TRÚC HÓA HỌC: Khi mô tả cấu trúc phức tạp (mạch vòng, mạch nhánh), TUYỆT ĐỐI KHÔNG SỬ DỤNG các lệnh vẽ hình học (như \\begin{array}, \\diagdown). Ưu tiên sử dụng Danh pháp IUPAC, Công thức phân tử và Ký hiệu SMILES (Ví dụ: Cyclohexane có SMILES là C1CCCCC1) để đảm bảo tính chính xác và dễ đọc.\n\n"
        
        "D. QUY TẮC TRẢ LỜI BÀI TẬP (Có số liệu/yêu cầu tính toán):\n"
        "  - LUÔN hỏi học sinh: 'Em muốn được hướng dẫn từng bước hay giải chi tiết?'\n"
        "  - Trình bày lời giải chi tiết theo các bước logic và chuyên nghiệp."
    )
    
    # --- PHẦN 2: KHỞI TẠO CHAT SESSION (Config) ---
    try:
        # Khởi tạo Chat Session trước, System Instruction được truyền vào config
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.3
            )
        )
        
        # --- PHẦN 3: GỬI FILE ID và YÊU CẦU XÁC NHẬN (Trong Tin nhắn đầu tiên) ---
        
        list_parts = []
        # Thêm các file đã upload bằng fileId
        for file_name in LIST_FILES:
            uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
            # Sử dụng application/pdf vì các file là PDF
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="application/pdf")) 
        
        # Thêm câu lệnh yêu cầu AI xác nhận đã tải file và luật phân tầng (Cập nhật câu chào)
        initial_prompt = "Xin chào, thầy là gia sư Hoá học THCS, em có câu hỏi nào cho thầy không? (Đảm bảo sử dụng giọng điệu thân thiện, dùng từ 'thầy' và gọi học sinh là em)."
        # Buộc dùng text= cho tất cả các lời gọi from_text
        list_parts.append(types.Part.from_text(text=initial_prompt)) 

        # Gửi file ID trong tin nhắn đầu tiên của phiên chat để tạo ngữ cảnh
        first_response = chat.send_message(list_parts)
        
        initial_message_text = first_response.text
        
        # Trả về 3 giá trị, bao gồm tin nhắn phản hồi của AI
        return client, chat, initial_message_text
        
    except Exception as e:
        # Xử lý lỗi trong quá trình khởi tạo phiên chat
        st.error(f"❌ Lỗi khởi tạo phiên chat. Vui lòng kiểm tra File ID ({LIST_FILES}) và API Key: {e}")
        return None, None, None


# --- Sửa cách gọi hàm setup_chat_session ---
client, chat_session, initial_message = setup_chat_session()

# --- Giao diện Chatbot ---
if "messages" not in st.session_state:
    if initial_message:
        # Lấy initial_message trực tiếp từ hàm setup
        st.session_state.messages = [{"role": "assistant", "content": initial_message}]
    else:
        st.session_state.messages = [{"role": "assistant", "content": "Chào em! Đã sẵn sàng học Hóa."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- WIDGET TẢI FILE ẢNH ---
uploaded_file = st.file_uploader(
    "🖼️ Tải ảnh câu hỏi (tùy chọn)", 
    type=["jpg", "jpeg", "png"],
    key="image_uploader_widget"
)


if prompt := st.chat_input("Nhập câu hỏi..."):
    if not client:
        st.stop()

    # Loại bỏ các khoảng trắng thừa từ prompt
    cleaned_prompt = prompt.strip()

    # --- 1. CHUẨN BỊ TIN NHẮN (GỒM VĂN BẢN VÀ ẢNH) ---
    message_parts = []
    user_question_for_history = cleaned_prompt # Câu hỏi gốc của người dùng
    
    # 1a. Thêm file ảnh (nếu có)
    if uploaded_file is not None:
        try:
            image_bytes = uploaded_file.getvalue()
            
            # Xử lý MIME type an toàn (FIX LỖI TypeError)
            mime_type = uploaded_file.type if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"] else "image/jpeg"
            
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type 
            )
            message_parts.append(image_part)
            
            # Ghi vào lịch sử tin nhắn (kèm ghi chú ảnh)
            user_question_for_history = f"📝 Câu hỏi (kèm ảnh): {cleaned_prompt}"
            
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file ảnh: {e}. Vui lòng thử lại với file ảnh khác.")
            st.stop()
    
    st.session_state.messages.append({"role": "user", "content": user_question_for_history})

    # 1b. Thêm văn bản câu hỏi (Phải là phần tử cuối cùng)
    if cleaned_prompt:
        # FIX LỖI: Buộc dùng text= cho tất cả các lời gọi from_text
        message_parts.append(types.Part.from_text(text=cleaned_prompt))
    else:
        # Nếu người dùng chỉ tải ảnh và nhấn enter không nhập text
        message_parts.append(types.Part.from_text(text="Phân tích hình ảnh này."))


    # --- 2. HIỂN THỊ TIN NHẮN NGƯỜI DÙNG ---
    with st.chat_message("user"):
        # Hiển thị cả ảnh (nếu có) và văn bản
        if uploaded_file is not None:
            st.image(uploaded_file, caption=f"Ảnh câu hỏi đã tải lên: {uploaded_file.name}")
        st.markdown(cleaned_prompt)


    # --- 3. GỬI VÀ NHẬN PHẢN HỒI ---
    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích ảnh và cấp độ câu hỏi..."):
            try:
                # Gửi tin nhắn chứa cả văn bản và Part ảnh
                response = chat_session.send_message(message_parts)
                response_text = response.text
                
                # ----------------------------------------------------------------------
                # 🆕 PHẦN MỚI: KIỂM TRA PHẢN HỒI VÀ LƯU CÂU HỎI KHÔNG TRẢ LỜI ĐƯỢC
                # ----------------------------------------------------------------------
                if ERROR_MESSAGE_TAG in response_text:
                    # Loại bỏ ERROR_MESSAGE_TAG khỏi phản hồi trước khi hiển thị
                    display_text = response_text.replace(ERROR_MESSAGE_TAG, "").strip()
                    
                    # Lưu câu hỏi gốc (hoặc mô tả kèm ảnh) vào danh sách
                    if cleaned_prompt and cleaned_prompt != "Phân tích hình ảnh này.":
                         question_to_save = cleaned_prompt
                    elif uploaded_file is not None:
                         question_to_save = f"(Ảnh: {uploaded_file.name}) + {cleaned_prompt}"
                    else:
                         question_to_save = cleaned_prompt
                         
                    if question_to_save not in st.session_state.missing_questions:
                        st.session_state.missing_questions.append(question_to_save)
                        
                    st.markdown(display_text)
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    
                else:
                    # Trả lời bình thường
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                # ----------------------------------------------------------------------
                
            except Exception as e:
                st.error(f"Lỗi: {e}")
