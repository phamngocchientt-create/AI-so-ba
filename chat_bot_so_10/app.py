import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & CSS ZALO HOÀN HẢO
# ==================================================
st.set_page_config(
    page_title="Gia sư Hóa học THCS - THCS Phan Chu Trinh", 
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #f1f5f9;
    }

    .sidebar-card {
        background: #ffffff;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }

    /* XÓA ĐỊNH DẠNG MẶC ĐỊNH CỦA KHUNG CHAT STREAMLIT */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 24px !important;
        gap: 12px !important;
    }

    /* ĐỊNH DẠNG AVATAR CHIBI TRÒN */
    [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
        width: 44px !important;
        height: 44px !important;
        border-radius: 50% !important;
        border: 2px solid #ffffff !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.12) !important;
        background-color: #fff !important;
    }

    /* 💬 TIN NHẮN HỌC SINH (BÊN PHẢI - MÀU XANH ZALO) */
    [data-testid="stChatMessage"]:has(.user-anchor) {
        flex-direction: row-reverse !important;
    }
    [data-testid="stChatMessage"]:has(.user-anchor) [data-testid="stChatMessageContent"] {
        background-color: #0068ff !important;
        color: #ffffff !important;
        border-radius: 20px 4px 20px 20px !important;
        box-shadow: 0 4px 12px rgba(0, 104, 255, 0.22) !important;
        padding: 12px 20px !important;
        max-width: 80% !important;
    }
    [data-testid="stChatMessage"]:has(.user-anchor) [data-testid="stChatMessageContent"] * {
        color: #ffffff !important;
    }

    /* 💬 TIN NHẮN THẦY GIÁO (BÊN TRÁI - NỀN TRẮNG SANG TRỌNG) */
    [data-testid="stChatMessage"]:has(.assistant-anchor) {
        flex-direction: row !important;
    }
    [data-testid="stChatMessage"]:has(.assistant-anchor) [data-testid="stChatMessageContent"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-radius: 4px 20px 20px 20px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05) !important;
        padding: 16px 24px !important;
        max-width: 85% !important;
        line-height: 1.6 !important;
    }
    
    [data-testid="stChatMessage"]:has(.assistant-anchor) [data-testid="stChatMessageContent"] h3 {
        color: #0284c7 !important;
        font-size: 1.1em !important;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 5px;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    /* KÍCH THƯỚC TO TOÁN HỌC LATEX */
    .katex {
        font-size: 1.12em !important;
    }

    /* KHUNG NHẬP LIỆU BÊN DƯỚI */
    [data-testid="stChatInput"] {
        border-radius: 30px !important;
        border: 2px solid #38bdf8 !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15) !important;
        padding: 4px 8px !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #0284c7 !important;
    }
    [data-testid="stChatInputSubmitButton"] {
        background-color: #0284c7 !important;
        color: white !important;
        border-radius: 50% !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 📂 NẠP AVATAR & QUẢN LÝ DỮ LIỆU
# ==================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")
PASSWORD_KEY = "CLEAR_PASSWORD"

def get_image_base64(base_name):
    for ext in [".PNG", ".png", ".jpg", ".jpeg", ".JPG", ".JPEG"]:
        path = os.path.join(CURRENT_DIR, f"{base_name}{ext}")
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
                ext_type = "png" if "png" in ext.lower() else "jpeg"
                return f"data:image/{ext_type};base64,{encoded}"
    return None

TEACHER_B64 = get_image_base64("teacher_avatar")
STUDENT_B64 = get_image_base64("student_avatar")

AVATAR_TEACHER_SRC = TEACHER_B64 if TEACHER_B64 else "https://api.dicebear.com/7.x/bottts/svg?seed=Teacher"
AVATAR_STUDENT_SRC = STUDENT_B64 if STUDENT_B64 else "https://api.dicebear.com/7.x/avataaars/svg?seed=Student"

# 🧪 HÀM TIỀN XỬ LÝ: CHỐNG DÍNH PHƯƠNG TRÌNH HÓA HỌC
def process_ai_response(text):
    if not text: 
        return ""
    
    # 1. Chuẩn hóa mũi tên nhiệt độ cho chuẩn KaTeX
    text = text.replace(r'\xrightarrow{t^\circ}', r'\xrightarrow{t^o}')
    text = text.replace(r'\xrightarrow{t^{\circ}}', r'\xrightarrow{t^o}')
    
    # 2. Tìm các pt đang kẹp $...$ (có mũi tên phản ứng) -> Đổi thành khối block $$...$$
    text = re.sub(r'(?<!\$)\$([^$]+?(?:\\rightarrow|\\longrightarrow|\\xrightarrow)[^$]+?)\$(?!\$)', r'$$\1$$', text)
    
    # 3. CHỐNG DÍNH CHÙM: Ép mọi cặp $$ phải nằm độc lập trên 1 dòng mới
    text = re.sub(r'\s*\$\$\s*', r'\n$$\n', text)
    
    # 4. Dọn dẹp khoảng trắng thừa do cắt dòng
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_value
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

HARDCODED_GREETING = "Xin chào em! Thầy là Gia sư Hóa học THCS. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# 📚 ĐỌC TÀI LIỆU DỰ PHÒNG
# ==================================================
DOC_FILES = ["tai_lieu_hoa.txt", "giao_an_hoa.txt", "tai_lieu_hoa.pdf"]
knowledge_base_text = ""
has_rag_data = False

for doc_name in DOC_FILES:
    doc_path = os.path.join(CURRENT_DIR, doc_name)
    if os.path.exists(doc_path):
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                knowledge_base_text = f.read().strip()
                if knowledge_base_text:
                    has_rag_data = True
                    break
        except Exception:
            pass

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Lỗi kết nối Gemini API: {e}")

# 🔑 SYSTEM INSTRUCTION CỦA AI (BẢN CHUẨN SƯ PHẠM - CHUYÊN HÓA)
# ==================================================
BASE_INSTRUCTION = r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Khoa học tự nhiên (phân môn Hóa học khối 8-9) tại trường THCS Phan Chu Trinh (xã Krông Búk).
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm.
- Mục tiêu: Không chủ động giải thay, ưu tiên dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình GDPT 2018 cấp THCS (phân môn Hóa học). Tuyệt đối không đưa kiến thức THPT/Đại học vào bài giảng.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Iron(III) oxide, Sulfate...). TUYỆT ĐỐI KHÔNG dùng tên cũ (Sắt, Nhôm, Đồng,..).
3. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là $24,79 \text{ L/mol}$ (tại $25^\circ\text{C}, 1 \text{ bar}$).
4. ĐIỀU KIỆN TIÊU CHUẨN (ĐKTC): Chỉ dùng $22,4 \text{ L/mol}$ khi HS yêu cầu ĐÍCH DANH.
5. ĐƠN VỊ: Khối lượng nguyên tử dùng "amu". Áp suất dùng "bar".

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
1. CÂU HỎI LÝ THUYẾT: 
   - Trả lời trực tiếp, rõ ràng. Nếu em hỏi kiến thức cơ bản, dùng kiến thức cơ bản. Nếu em hỏi "tại sao", mới dùng kiến thức giải thích sâu. Kiến thức nâng cao chỉ trả lời nếu học sinh muốn tìm hiểu mở rộng kiến thức.
2. CÂU HỎI BÀI TẬP (TÍNH TOÁN/LÝ THUYẾT): 
   - Khi được hỏi về một bài tập (có thể là bài tập về lí thuyết - vận dụng lí thuyết để giải quyết bài toán định tính hoặc bài tập tính toán). Hãy chào đón và đưa ra 3 lựa chọn:
     * Lựa chọn A: Thầy sẽ hướng dẫn em tư duy từng bước, chúng ta cùng nhau giải quyết bài tập đó (Khuyên dùng).
     * Lựa chọn B: Thầy đưa ra "bản đồ" (phác thảo các bước giải) sau đó em dựa vào đó để tự giải quyết bài tập đó.
     * Lựa chọn C: Thầy sẽ đưa ra đáp án chi tiết của bài tập mà em đưa để em đối chiếu.
   - Nếu học sinh chọn C (hoặc yêu cầu đáp án chi tiết), thì hãy vận dụng kiến thức đã được cung cấp trong tài liệu hoặc kiến thức nguồn của mình nếu TH kiến thức đó không có trong tài liệu để giải  bài toán mà học sinh đã đưa ở cau hỏi trước đó, yêu cầu đầy đủ lời giải, công thức và phép tính (Không ghi Bước 1, Bước 2, không giải thích lề mề, không hướng dẫn trong bài giải chi tiết nữa). 
   - Lưu ý: bài giải chi tiết đucojw cung cấp trong tài liệu khong phải là bài giải chi tiết của tất cả các bài tập, chỉ là đáp án chi tiết của bài tập đó mà thôi.
Để câu trả lời đẹp như "viết bảng", bạn PHẢI tuân thủ:
1. KHOẢNG TRẮNG: Sử dụng "Dòng trống" (Double Enter) giữa các đoạn văn, giữa đề mục và nội dung.
2. ĐỀ MỤC: Các mục lớn (I, II, III...), mục nhỏ (a, b, c...) hoặc số thứ tự (1, 2, 3...) phải **IN ĐẬM** và đứng riêng một dòng.
3. PHƯƠNG TRÌNH HÓA HỌC (PTHH):
   - Phải bọc trong $$...$$ và nằm trên dòng riêng biệt.
   - Mỗi PTHH là một dòng riêng. Tuyệt đối không để 2 PTHH trên cùng 1 dòng.
   - Giữa các PTHH liên tiếp phải có một dòng trống.
4. CÔNG THỨC & LATEX:
   - Công thức hóa học/toán học bọc trong $...$ (cùng dòng) hoặc $$...$$ (riêng dòng).
   - Ví dụ: $Al_2O_3$, $n = \frac{m}{M}$.
   - Không dùng ký hiệu lạ như \ce, \text. Tách chữ và số rõ ràng.

# ❤️ PHONG CÁCH & KẾT THÚC
- Luôn khích lệ: "Thầy tin em làm được", "Giỏi lắm", "Cố gắng lên nhé". Đặc biệt sát sao động viên tinh thần tự giác của các em.
- Kết thúc: Luôn bằng một câu hỏi gợi mở hoặc kiểm tra sự thấu hiểu của học sinh.
"""
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của Thầy. Thầy sẽ sớm cập nhật kiến thức này. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác không?"

if has_rag_data:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n\nTÀI LIỆU CỦA THẦY:\n{knowledge_base_text}\n\n1. CHỈ TRẢ LỜI dựa trên tài liệu. 2. Nếu không có, trả về: {ERROR_MESSAGE_TAG}"""
else:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n- Trả lời bằng tri thức Hóa học THCS chuẩn. Nếu ngoài phạm vi, trả về: {ERROR_MESSAGE_TAG}"""

# ==================================================
# 📌 THANH BÊN TRÁI (SIDEBAR)
# ==================================================
with st.sidebar:
    st.title("🧪 Lớp Hóa Học THCS")
    st.caption("Trường THCS Phan Chu Trinh - Krông Búk")
    st.divider()

    if has_rag_data:
        st.success("📚 **Đang dùng:** Tài liệu Giáo án riêng")
    else:
        st.warning("⚡ **Đang dùng:** Tri thức mở")

    st.divider()
    st.header("📝 Câu hỏi Cần Bổ Sung")
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions, 1):
            st.markdown(f"**{i}.** {q}")
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            if st.form_submit_button("Xóa Toàn bộ"):
                if password == st.secrets.get(PASSWORD_KEY, "admin123"):
                    st.session_state.missing_questions = []
                    save_data(STORAGE_FILE, [])
                    st.success("✅ Đã xóa!")
                    st.rerun()
                else: 
                    st.error("❌ Sai mật khẩu.")
    else:
        st.write("Không có câu hỏi nào.")
    st.divider()
    if st.button("🗑️ Xóa lịch sử", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

# ==================================================
# 🏛️ KHU VỰC HIỂN THỊ CHÍNH
# ==================================================
banner_loaded = False
for name in ["banner.png", "banner.PNG", "banner.jpg", "banner.jpeg", "banner.JPG"]:
    banner_path = os.path.join(CURRENT_DIR, name)
    if os.path.exists(banner_path):
        st.image(banner_path, use_container_width=True)
        banner_loaded = True
        break
if not banner_loaded:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 1.5rem; border-radius: 16px; color: white; text-align: center; margin-bottom: 1.5rem;">
        <h2 style="margin:0; font-size: 1.8rem;">🧪 GIA SƯ HOÁ HỌC THCS</h2>
        <p style="margin:5px 0 0 0; opacity: 0.9;">TRƯỜNG THCS PHAN CHU TRINH - KRÔNG BÚK</p>
    </div>
    """, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# 📍 HÀM HIỂN THỊ TIN NHẮN 
def render_zalo_chat(role, content):
    if role == "user":
        avatar_src = AVATAR_STUDENT_SRC
        anchor = "<span class='user-anchor'></span>"
    else:
        avatar_src = AVATAR_TEACHER_SRC
        anchor = "<span class='assistant-anchor'></span>"
        # XỬ LÝ CÔNG THỨC TRƯỚC KHI RENDER
        content = process_ai_response(content)
        
    with st.chat_message(role, avatar=avatar_src):
        st.markdown(f"{anchor}\n{content}", unsafe_allow_html=True)

# 💬 HIỂN THỊ LỊCH SỬ CHAT
for msg in st.session_state.messages:
    render_zalo_chat(msg["role"], msg["content"])

# ==================================================
# 🧹 NÚT XÓA BẢNG NẰM DƯỚI CÙNG (NGAY TRÊN THANH GÕ CHAT)
# ==================================================
st.markdown("<br>", unsafe_allow_html=True)

# Chỉ hiển thị nút "Xóa bảng" nếu học sinh đã bắt đầu chat (nhiều hơn 1 tin nhắn mặc định)
if len(st.session_state.messages) > 1:
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        if st.button("✨ XOÁ LỊCH SỬ CHAT THƯỜNG XUYÊN ĐỂ CHẠY MƯỢT MÀ NHÉ CÁC EM, BẤM VÀO ĐÂY ĐỂ XOÁ NÈ ✨", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
            save_data(HISTORY_FILE, st.session_state.messages)
            st.rerun()

st.markdown("<br><br><br>", unsafe_allow_html=True)

# ==================================================
# 🤖 KHU VỰC NHẬP LIỆU & XỬ LÝ LOGIC
# ==================================================
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh", type=["jpg", "jpeg", "png"], key="uploader")
prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào...")

if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    
    # Lấy nội dung hiển thị cho UI
    user_msg_content = cleaned_prompt
    if uploaded_file:
        user_msg_content = f"📝 (Kèm ảnh) {cleaned_prompt}"

    # 1. Lưu tin nhắn của user vào session_state (lịch sử cục bộ)
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)

    render_zalo_chat("user", cleaned_prompt)

    with st.chat_message("assistant", avatar=AVATAR_TEACHER_SRC):
        st.markdown("<span class='assistant-anchor'></span>", unsafe_allow_html=True)
        with st.spinner("Thầy đang xem bài..."):
            try:
                # 🔴 CHÌA KHÓA CHỐNG MẤT TRÍ NHỚ: GÓI TOÀN BỘ LỊCH SỬ GỬI CHO AI
                gemini_history = []
                
                # Duyệt qua lịch sử (trừ tin nhắn vừa nhập)
                for msg in st.session_state.messages[:-1]:
                    # Gemini dùng 'model' thay vì 'assistant'
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
                    )
                
                # 2. Xử lý tin nhắn mới nhất (kèm ảnh nếu có)
                message_parts = []
                if uploaded_file:
                    message_parts.append(types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
                message_parts.append(types.Part.from_text(text=cleaned_prompt))
                
                gemini_history.append(types.Content(role="user", parts=message_parts))

                # 3. Gửi toàn bộ lịch sử (gemini_history) vào API
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2 if has_rag_data else 0.3
                    )
                )
                res_text = response.text.strip()
                
                if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                    if cleaned_prompt not in st.session_state.missing_questions:
                        st.session_state.missing_questions.append(cleaned_prompt)
                        save_data(STORAGE_FILE, st.session_state.missing_questions)
                    final_res = ERROR_MESSAGE
                else:
                    final_res = res_text

                # 4. Lưu câu trả lời của AI vào lịch sử
                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_data(HISTORY_FILE, st.session_state.messages)
                st.rerun()
                
            except Exception as e:
                st.error(f"Thầy gặp sự cố kết nối: {e}")
