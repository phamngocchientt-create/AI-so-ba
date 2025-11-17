import streamlit as st
from google import genai
from google.genai import types
import os

# ==================================================
# 📌 BƯỚC 1: DÁN DANH SÁCH FILE ID CỦA BẠN VÀO ĐÂY
# ==================================================
# DÁN fileId THỰC TẾ CỦA BẠN
LIST_FILES = ['files/t78ccqj6zlsg', 'files/reskuozgl4rb']
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

    # Đọc khóa API từ Streamlit Secrets
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Lỗi cấu hình: Không tìm thấy GEMINI_API_KEY trong Streamlit Secrets.")
        return None, None

    client = genai.Client(api_key=api_key)

    # --- PHẦN 1: TẠO SYSTEM INSTRUCTION ---
    sys_instruct = (
    "Bạn là Gia sư Hóa học THCS thông minh, thân thiện, và tuân thủ Chương trình Phổ thông 2018.\n\n"
    "[QUY TẮC PHÂN TẦNG KIẾN THỨC BẮT BUỘC] Tài liệu của bạn được chia thành 4 mục: [KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].\n\n"
    
    "QUY TẮC TRẢ LỜI LÝ THUYẾT (Tuân thủ Ưu tiên):\n"
    "1. Mặc định (Hỏi khái niệm/lý thuyết): **CHỈ** được lấy thông tin từ mục **[KIẾN THỨC CƠ BẢN]**. KHÔNG bao gồm thông tin từ các mục khác.\n"
    "2. Hỏi 'Tại sao', 'Vì sao', 'Giải thích': **CHỈ** được lấy thông tin từ mục **[PHẦN GIẢI THÍCH]**.\n"
    "3. Hỏi 'Nâng cao', 'Đặc biệt', 'Mở rộng': **CHỈ** được lấy thông tin từ mục **[PHẦN NÂNG CAO]**.\n"
    "4. Nếu thông tin không có: Nói rõ 'Thầy/Cô xin lỗi, thông tin này không có trong tài liệu...'\n"
    
    "NGÔN NGỮ & ĐỊNH DẠNG:\n"
    "A. Luôn sử dụng danh pháp Hóa học mới (VD: acid, base, oxide, oxygen, hydrogen). \n"
    "B. QUY TẮC THỂ TÍCH KHÍ: ƯU TIÊN TUYỆT ĐỐI $n = V/22.4$ nếu có cụm từ 'đktc'; nếu không, dùng $n = V/24.79$.\n"
    "C. QUY TẮC HIỂN THỊ PHƯƠNG TRÌNH: Dùng $$display$$ và ngắt dòng rõ ràng.\n"
    "D. QUAN TRỌNG VỀ HỆ PHƯƠNG TRÌNH: Trình bày hệ phương trình theo quy tắc siêu tối giản (các phương trình riêng biệt), kết quả giải hệ bằng **VĂN BẢN THUẦN TÚY**.\n\n"
    
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
            
            # ✅ FIX LỖI MIME TYPE: Dùng text/plain (rất ổn định cho nội dung tài liệu)
            list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain")) 
        
        # Thêm câu lệnh yêu cầu AI xác nhận đã tải file và luật phân tầng
        initial_message = f"Tôi đã tải lên {len(LIST_FILES)} tài liệu học tập. Hãy đọc kỹ tài liệu này, tuân thủ nghiêm ngặt các QUY TẮC TRẢ LỜI. Sau đó, hãy chào hỏi học sinh và xác nhận rằng bạn đã sẵn sàng."
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
        # Lấy tin nhắn cuối cùng (là lời chào của AI)
        # Sử dụng len(chat_session.get_history()) - 1 để đảm bảo index
        history = chat_session.get_history()
        # Lời chào là phản hồi của model cho tin nhắn gửi file (luôn là tin nhắn cuối cùng)
        first_message = history[-1].parts[0].text 
        st.session_state.messages = [{"role": "assistant", "content": first_message}]
    else:
        # Lời chào mặc định nếu có lỗi xảy ra
        st.session_state.messages = [{"role": "assistant", "content": "Chào em! Đã sẵn sàng học Hóa."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi..."):
    if not client:
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích cấp độ câu hỏi và tìm kiếm tài liệu..."):
            try:
                # Gửi tin nhắn tiếp theo
                response = chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Lỗi: {e}")

















