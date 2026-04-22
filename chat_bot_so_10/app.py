import streamlit as st
from google import genai
from google.genai import types
import os
import io 
import json 
import time

# ==================================================
# 📌 CẤU HÌNH HỆ THỐNG
# ==================================================
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác trong chương trình Hóa học THCS không?"
PASSWORD_KEY = "CLEAR_PASSWORD" 
HARDCODED_GREETING = "Xin chào, thầy là Gia sư Hoá học THCS, em có câu hỏi nào cho thầy không"

# --- HÀM XỬ LÝ JSON ---
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

if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])

with st.sidebar:
    # Tự động quét và báo cáo số lượng tài liệu .txt trong thư mục files/
    txt_files = [f for f in os.listdir("files") if f.endswith(".txt")] if os.path.exists("files") else []
    st.success(f"✅ Đã kết nối {len(txt_files)} tài liệu tri thức.")
    
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
# ⚙️ CẤU HÌNH CHAT SESSION (NẠP TRỰC TIẾP - CHỐNG LỖI 429)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None 

    # Dùng v1beta để hỗ trợ tốt nhất cho Gemini 2.0
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # --- ĐỌC TÀI LIỆU TRỰC TIẾP TỪ THƯ MỤC FILES/ ---
    knowledge_base = ""
    if os.path.exists("files"):
        for filename in os.listdir("files"):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join("files", filename), "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- DỮ LIỆU TỪ FILE {filename} ---\n" + f.read()
                except: pass

    # --- GIỮ NGUYÊN PROMPT CỦA THẦY ---
    prompt_engineering = (r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS, hoạt động theo kiến thức chương trình GDPT 2018, lưu ý hãy sử dụng danh pháp quốc tế theo chương trình GDPT 2018. 
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em". 
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm trường Phan Chu Trinh.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING 3 CẤP ĐỘ)
Khi học sinh hỏi bài tập, bạn không được giải ngay. Hãy thực hiện theo quy trình:

## Bước 1: Chào đón & Chẩn đoán
Xác định dạng bài và khen ngợi sự chủ động của em. Sau đó, đưa ra 3 lựa chọn để em quyết định cách học:
- **Lựa chọn A:** Thầy hướng dẫn em tư duy từng bước một (Khuyên dùng để hiểu sâu).
- **Lựa chọn B:** Thầy đưa ra "bản đồ" (phác thảo các bước giải) để em tự đi.
- **Lựa chọn C:** Thầy đưa bài giải chi tiết để em đối chiếu (Chỉ dùng khi em thực sự bí).

## Bước 2: Dẫn dắt (Nếu em chọn A hoặc B)
- Tuyệt đối không làm thay các phép tính cộng, trừ, nhân, chia. 
- Hãy hỏi ngược lại: "Để tính số mol của $O_2$, em nhớ công thức nào liên quan đến thể tích ở điều kiện chuẩn không?"
- Chỉ cung cấp "cần câu", không cung cấp "con cá".

## Bước 3: Kiểm soát chất lượng
- Nếu học sinh đưa ra kết quả sai, hãy nhẹ nhàng chỉ ra lỗi sai ở bước nào (ví dụ: quên cân bằng, nhầm khối lượng mol).
- Luôn kết thúc bằng một câu khích lệ và hỏi xem em có muốn thầy giải thích thêm phần nào không.

# 🧩 CHIẾN LƯỢC TRUY XUẤT PHÂN TẦNG (XML TAG LOGIC)
Dữ liệu của Thầy được cấu trúc qua các thẻ. Bạn PHẢI tuân thủ quy tắc gắp dữ liệu sau:

1. CÂU HỎI KHÁI NIỆM/ĐỊNH NGHĨA:
   - Ưu tiên: Sử dụng kiến thức trong thẻ `<co_ban>`.
   - HÀNH ĐỘNG: TRẢ LỜI TRỰC TIẾP và ĐẦY ĐỦ. Không hỏi ngược khi học sinh đang cần nạp kiến thức mới. 
   - Mở rộng: Nếu học sinh hỏi "tại sao" hoặc tỏ ý chưa hiểu, hãy dùng nội dung trong thẻ `<giai_thich>`.
   - KẾT THÚC: Đưa ra một ví dụ minh họa hoặc một câu hỏi nhỏ để kiểm tra xem học sinh đã hiểu khái niệm đó chưa.

2. CÂU HỎI BÀI TẬP/VẬN DỤNG:
   - Ưu tiên: Sử dụng nội dung trong thẻ `<huong_dan_giai>`.
   - Quy tắc thép: Tuyệt đối không trích xuất thẻ `<bai_giai_chi_tiet>` ở lượt trả lời đầu tiên. Hãy dùng thẻ hướng dẫn để tạo "Giàn giáo tri thức" (Scaffolding).
   - Chỉ đưa `<bai_giai_chi_tiet>` khi học sinh chọn "Lựa chọn C" hoặc đã thử giải nhưng sai hoàn toàn.
   - Lưu ý khi đưa ra bài giải chi tiết nếu học sinh yêu cầu, thì chỉ đưa ra 1 bài giải với đầy đủ lời giải, công thức áp dụng và phép tính, không ghi các bước nữa (Bước 1, Bước 2, Bước 3,...)
   - CÁCH LÀM (VẬN DỤNG THÔNG MINH): 
      * Nếu bài tập đó chưa có mẫu trong file, hãy sử dụng CÔNG THỨC và LÝ THUYẾT có sẵn trong thư viện để phân tích -> Từ đó đưa ra lời giải hợp lí cho HS.
      * Nhận diện các đại lượng đề bài cho -> Đối chiếu với công thức trong file -> Hướng dẫn học sinh tính toán, giải bài tập. 
      * Trường hợp nếu là một bài tập quá khó, vượt qua tầm với của bạn, thì hãy từ chối, đừng đưa kiến thức mà bạn ko chắc chắn nó có đúng hay không.
    - QUY TRÌNH HƯỚNG DẪN:
      * Chào đón và xác định dạng bài: "Thầy đã nhận được bài của em về [Chủ đề]..."
      * Gợi mở bước 1: "Để giải bài này, trước hết em hãy nhìn vào công thức [Tên công thức] trong bài học, em thử tính số mol của chất X trước nhé?"
      * Tuyệt đối KHÔNG đưa bài giải chi tiết ngay từ câu đầu tiên trừ khi học sinh yêu cầu khẩn thiết.
3. CÂU HỎI MỞ RỘNG/HỌC SINH GIỎI:
   - Chỉ sử dụng nội dung trong thẻ `<nang_cao>` khi học sinh yêu cầu bài tập khó hoặc hỏi về các trường hợp đặc biệt.

# 📐 QUY TẮC HIỂN THỊ & LATEX (BẮT BUỘC)
Để tránh lỗi hiển thị code và dính chữ, bạn phải tuân thủ:
1. Công thức hóa học/Toán học: Phải bọc trong $...$ hoặc $$...$$. 
   - Ví dụ: $H_2SO_4$, $n = \frac{m}{M}$.
2. PTHH: BẮT BUỘC đặt trong cặp $$...$$ trên một dòng riêng biệt. Không để PTHH dính vào văn bản.
3. NGĂN CÁCH: Giữa hai khối PTHH hoặc giữa văn bản và PTHH PHẢI có ít nhất một dòng trống.
4. Đơn vị: Viết bình thường: 10 g, 0,5 mol.
5. Tuyệt đối: Không hiển thị mã code thô.

# 📚 QUY TẮC TRI THỨC (RAG & GIỚI HẠN)
1. NGUỒN KIẾN THỨC: Chỉ trả lời dựa trên kho tri thức đã được nạp bên dưới. 
2. XỬ LÝ KHI THIẾU DỮ LIỆU: Phản hồi theo mẫu ERROR_MESSAGE đã định và kèm mã [MISSING_DOC].
3. CHUẨN IUPAC: Luôn dùng danh pháp tiếng Anh và điều kiện chuẩn (24,79 L).

# ❤️ PHONG CÁCH SƯ PHẠM
- Ngôn ngữ: Nhẹ nhàng, khích lệ. Kết thúc bằng một câu hỏi gợi mở.
    """)

    # Kết hợp Prompt và Tài liệu (Dùng dấu + để an toàn tuyệt đối với dấu ngoặc nhọn LaTeX)
    full_instruction = prompt_engineering + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP (DỮ LIỆU GỐC):\n" + knowledge_base

    try:
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.2)
        )
        return client, chat
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        return None, None

client, chat_session = setup_chat_session() 

# ==================================================
# 🤖 GIAO DIỆN VÀ XỬ LÝ TIN NHẮN
# ==================================================
chat_placeholder = st.container()

with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="fixed_bottom_uploader")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    message_parts = []
    
    user_msg_content = cleaned_prompt
    if uploaded_file:
        image_part = types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type)
        message_parts.append(image_part)
        user_msg_content = f"📝 (Kèm ảnh) {cleaned_prompt}"
    
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)

    with chat_placeholder:
        with st.chat_message("user"):
            if uploaded_file: st.image(uploaded_file, width=300)
            st.markdown(cleaned_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thầy đang xem bài..."):
                try:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
                    
                    # Cơ chế Tự động thử lại (Retry) nếu học sinh hỏi quá nhanh gây lỗi 429
                    response = None
                    for attempt in range(3):
                        try:
                            response = chat_session.send_message(message_parts)
                            break
                        except Exception as e:
                            if "429" in str(e) and attempt < 2:
                                time.sleep(5)
                                continue
                            else: raise e

                    res_text = response.text.strip()
                    
                    if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                        if cleaned_prompt not in st.session_state.missing_questions:
                            st.session_state.missing_questions.append(cleaned_prompt)
                            save_data(STORAGE_FILE, st.session_state.missing_questions)
                        final_res = ERROR_MESSAGE
                    else:
                        final_res = res_text

                    st.markdown(final_res)
                    st.session_state.messages.append({"role": "assistant", "content": final_res})
                    save_data(HISTORY_FILE, st.session_state.messages)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}. Em hãy đợi 10 giây rồi thử lại nhé!")
