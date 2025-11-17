import streamlit as st
from google import genai
from google.genai import types
import os

# ==================================================
# 📌 BƯỚC 1: DÁN DANH SÁCH FILE ID CỦA BẠN VÀO ĐÂY
# Lấy từ output của script upload_knowledge.py
# ==================================================
# Ví dụ mẫu. BẠN CẦN THAY THẾ BẰNG fileId THỰC TẾ CỦA MÌNH
LIST_FILES = ['files/r222i4dmmhc0', 'files/clhq5xs9q2tb', 'files/0unn16phn0hc']
# ==================================================

st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Phân hóa trình độ")

with st.sidebar:
    st.success(f"✅ Đã kết nối {len(LIST_FILES)} tài liệu.")
    st.info("🤖 Model: gemini-2.5-flash")  # Cập nhật lên Gemini 2.5 Flash
    with st.expander("Hướng dẫn phân tầng kiến thức"):
        st.write("- Hỏi lý thuyết thông thường: Trả lời từ **[KIẾN THỨC CƠ BẢN]**.")
        st.write("- Hỏi 'Tại sao/Vì sao/Giải thích': Trả lời từ **[PHẦN GIẢI THÍCH]**.")
        st.write("- Hỏi 'Nâng cao/Đặc biệt': Trả lời từ **[PHẦN NÂNG CAO]**.")
        st.write("- Hỏi 'Giải chi tiết/Bài tập': Trả lời từ **[BÀI TẬP VÀ GIẢI CHI TIẾT]**.")


@st.cache_resource
def setup_chat_session():
    """Thiết lập phiên chat, đọc khóa API từ Streamlit Secrets, và tải file."""

    # Đọc khóa API từ Streamlit Secrets
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("❌ Lỗi cấu hình: Không tìm thấy GEMINI_API_KEY trong Streamlit Secrets.")
        return None, None

    client = genai.Client(api_key=api_key)

    # --- PHẦN QUAN TRỌNG NHẤT: LUẬT PHÂN TẦNG KIẾN THỨC (System Instruction) ---
    sys_instruct = (
        "Bạn là Gia sư Hóa học THCS thông minh và thân thiện. Tài liệu của bạn được chia thành 4 phần: "
        "[KIẾN THỨC CƠ BẢN], [PHẦN GIẢI THÍCH], [PHẦN NÂNG CAO], và [BÀI TẬP VÀ GIẢI CHI TIẾT].\n\n"
        "QUY TẮC TRẢ LỜI NGHIÊM NGẶT:\n"
        "1. Mặc định (Hỏi lý thuyết): Chỉ lấy thông tin từ mục [KIẾN THỨC CƠ BẢN]. Trả lời ngắn gọn, dễ hiểu.\n"
        "2. Khi học sinh hỏi 'Tại sao', 'Vì sao', 'Giải thích': Hãy dùng thông tin từ mục [PHẦN GIẢI THÍCH] để làm rõ vấn đề.\n"
        "3. Khi học sinh hỏi 'Nâng cao', 'Có gì đặc biệt', 'Mở rộng': Mới được phép dùng thông tin từ mục [PHẦN NÂNG CAO].\n"
        "4. Khi học sinh hỏi bài tập tính toán hoặc 'Giải chi tiết': Hãy dùng mục [BÀI TẬP VÀ GIẢI CHI TIẾT] để hướng dẫn từng bước.\n"
        "5. Nếu thông tin không có trong BẤT KỲ MỤC nào của tài liệu, hãy nói rõ là 'Thầy/Cô xin lỗi, thông tin này không có trong tài liệu chúng ta đang sử dụng.'\n"
    )

    # Tạo danh sách file để đưa vào AI
    list_parts = []
    # Thêm các file đã upload bằng fileId
    for file_name in LIST_FILES:
        # Đường dẫn URI phải theo format của Gemini
        uri_path = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
        # Mime type là text/plain vì chúng ta chỉ đang tải văn bản
        list_parts.append(types.Part.from_uri(file_uri=uri_path, mime_type="text/plain"))

    # Thêm lời nhắc cuối cùng và Lời chào ban đầu
    # CODE MỚI (Khắc phục lỗi 400 INVALID_ARGUMENT)

    list_parts.append(types.Part.from_text(text="Hãy tuân thủ cấu trúc tài liệu trên."))
    
    initial_greeting = "Chào em! Thầy đã đọc kỹ tài liệu. Thầy sẽ trả lời kiến thức cơ bản trừ khi em hỏi 'tại sao' hay 'nâng cao'."

    try:
        # Bước A: Gửi tài liệu (list_parts), System Instruction, và yêu cầu xác nhận.
        # Lưu ý: Chúng ta dùng generate_content() vì nó hỗ trợ truyền file IDs trực tiếp.
        initial_parts = list_parts + [
            types.Part.from_text(text=sys_instruct),
            types.Part.from_text(text=f"Tôi đã tải lên {len(LIST_FILES)} tài liệu. Hãy xác nhận rằng bạn đã hiểu rõ quy tắc phân tầng kiến thức và sẵn sàng trả lời bằng lời chào sau: '{initial_greeting}'")
        ]

        initial_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=initial_parts, # TRUYỀN FILE IDs VÀO ĐÂY LÀ ĐÚNG CÁCH
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        
        # Bước B: Khởi tạo Chat Session và sử dụng kết quả xác nhận làm history đầu tiên.
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.3
            ),
            # Khởi tạo history bằng tin nhắn đầu tiên đã xác nhận (Gửi File/Instruction và Phản hồi của AI)
            history=[
                types.Content(role="user", parts=initial_parts),
                types.Content(role="model", parts=[types.Part.from_text(text=initial_response.text)])
            ]
        )
        return client, chat
     
    except Exception as e:
        # Xử lý lỗi trong quá trình khởi tạo phiên chat
        st.error(f"❌ Lỗi khởi tạo phiên chat. Vui lòng kiểm tra File ID và API Key: {e}")
        return None, None
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo phiên chat: {e}")
        return None, None


client, chat_session = setup_chat_session()

# --- Giao diện Chatbot ---
if "messages" not in st.session_state:
    # Lấy lời chào ban đầu từ history
    if chat_session and chat_session.get_history():
        first_message = chat_session.get_history()[-1].parts[0].text
        st.session_state.messages = [{"role": "assistant", "content": first_message}]
    else:
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
                response = chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:

                st.error(f"Lỗi: {e}")
