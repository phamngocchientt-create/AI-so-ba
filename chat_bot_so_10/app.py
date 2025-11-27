import streamlit as st
from google import genai
from google.genai import types
import os
import io # Cần thiết cho việc xử lý file ảnh

# ==================================================
# 📌 BƯỚC 1: DÁN DANH SÁCH FILE ID CỦA BẠN VÀO ĐÂY
# ==================================================
# DÁN fileId THỰC TẾ CỦA BẠN
LIST_FILES = ['files/jglrw07zy6f9', 'files/ituz5swks2c4', 'files/jkta6xti7p77', 'files/5ex8l5zjewb4']
# ==================================================

st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    st.info("🤖 Model: gemini-2.0-flash")
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
        return None, None

    client = genai.Client(api_key=api_key)

    # --- PHẦN 1: TẠO SYSTEM INSTRUCTION (Tối giản và Cố định) ---
    sys_instruct = (
        "Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.\n\n"
        "[QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].\n\n"
        
        "QUY TẮC TRẢ LỜI LÝ THUYẾT (Ưu tiên):\n"
        "1. Mặc định: CHỈ lấy thông tin từ mục **[KIẾN THỨC CƠ BẢN]**.\n"
        "2. Giải thích/Nâng cao: CHỈ lấy thông tin từ mục tương ứng **[PHẦN GIẢI THÍCH]** hoặc **[PHẦN NÂNG CAO]** khi được hỏi rõ.\n"
        
        "NGÔN NGỮ & ĐỊNH DẠNG (Bắt buộc):\n"
        "A. Danh pháp: Luôn sử dụng danh pháp Hóa học mới (VD: acid, base, oxide, oxygen, hydrogen).\n"
        "B. LỌC VĂN BẢN: TUYỆT ĐỐI KHÔNG được đưa chuỗi văn bản 'display' (hoặc 'Display') vào bất kỳ phần nào của câu trả lời. \n"
        "C. QUY TẮC THỂ TÍCH KHÍ: ƯU TIÊN TUYỆT ĐỐI $n = V/22.4$ nếu có cụm từ 'đktc'; nếu không, dùng $n = V/24.79$.\n"
        "D. QUY TẮC HIỂN THỊ (FIX DÍNH LIỀN & LỖI HỆ PHƯƠNG TRÌNH):\n"
        "   - Tất cả công thức/PTHH phải dùng **Display LaTeX** ($$...$$).\n"
        "   - BẮT BUỘC thêm **hai ngắt dòng** (ngắt dòng kép) giữa các phương trình liên tiếp.\n"
        "   - **QUAN TRỌNG VỀ HỆ PHƯƠNG TRÌNH:** Sau khi liệt kê các phương trình của hệ (1) và (2) bằng Display LaTeX:\n"
        "     - **TUYỆT ĐỐI BỎ QUA** các bước tính toán giải hệ phương trình.\n"
        "     - TRỰC TIẾP đưa **kết quả cuối cùng của các biến số** (ví dụ: 'Giải hệ, ta được x = 0.1 mol và y = 0.2 mol.') dưới dạng **VĂN BẢN THUẦN TÚY** (Không dùng LaTeX) và tiếp tục bài giải.\n\n"
        
        "QUY TẮC TRẢ LỜI BÀI TẬP (Có số liệu/yêu cầu tính toán):\n"
        "   - LUÔN hỏi học sinh: 'Em muốn được hướng dẫn từng bước hay giải chi tiết?'\n"
        "   - Trình bày lời giải chi tiết theo các bước logic và chuyên nghiệp."
    )
    
    # --- PHẦN 2: KHỞI TẠO CHAT SESSION (Chỉ dùng System Instruction) ---
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
            # Sử dụng text/plain vì đây là định dạng ổn định nhất cho tài liệu
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain")) 
        
        # Thêm câu lệnh yêu cầu AI xác nhận đã tải file và luật phân tầng
        initial_message = f"Tôi đã tải lên {len(LIST_FILES)} tài liệu học tập. Hãy đọc kỹ tài liệu này, tuân thủ nghiêm ngặt các QUY TẮC TRẢ LỜI. Sau đó, hãy chào hỏi học sinh và xác nhận rằng bạn đã sẵn sàng."
        # ✅ FIX LỖI: Buộc dùng text= cho tất cả các lời gọi from_text
        list_parts.append(types.Part.from_text(text=initial_message)) 

        # Gửi file ID trong tin nhắn đầu tiên của phiên chat để tạo ngữ cảnh
        first_response = chat.send_message(list_parts)
        
        return client, chat
        
    except Exception as e:
        # Xử lý lỗi trong quá trình khởi tạo phiên chat
        st.error(f"❌ Lỗi khởi tạo phiên chat. Vui lòng kiểm tra File ID ({LIST_FILES}) và API Key: {e}")
        return None, None


client, chat_session = setup_chat_session()

# --- Giao diện Chatbot ---
if "messages" not in st.session_state:
    # Lấy lời chào ban đầu từ history (Tin nhắn phản hồi của AI sau khi đọc file)
    if chat_session and chat_session.get_history():
        history = chat_session.get_history()
        first_message = history[-1].parts[0].text 
        st.session_state.messages = [{"role": "assistant", "content": first_message}]
    else:
        st.session_state.messages = [{"role": "assistant", "content": "Chào em! Đã sẵn sàng học Hóa."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- WIDGET TẢI FILE ẢNH ---
uploaded_file = st.file_uploader("🖼️ Tải ảnh câu hỏi (tùy chọn)", type=["jpg", "jpeg", "png"])


if prompt := st.chat_input("Nhập câu hỏi..."):
    if not client:
        st.stop()

    # Loại bỏ các khoảng trắng thừa từ prompt
    cleaned_prompt = prompt.strip()

    # --- 1. CHUẨN BỊ TIN NHẮN (GỒM VĂN BẢN VÀ ẢNH) ---
    message_parts = []
    
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
            st.session_state.messages.append({"role": "user", "content": f"📝 Câu hỏi (kèm ảnh): {cleaned_prompt}"})
            
        except Exception as e:
            st.error(f"❌ Lỗi xử lý file ảnh: {e}. Vui lòng thử lại với file ảnh khác.")
            st.stop()
    else:
        # Nếu không có ảnh, ghi tin nhắn thuần túy vào lịch sử
        st.session_state.messages.append({"role": "user", "content": cleaned_prompt})
        

    # 1b. Thêm văn bản câu hỏi (Phải là phần tử cuối cùng)
    # ✅ FIX LỖI: Buộc dùng text= cho tất cả các lời gọi from_text
    if cleaned_prompt:
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
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Lỗi: {e}")




