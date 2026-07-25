import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

# ==================================================
# 🎨 CẤU HÌNH TRANG & GIAO DIỆN BONG BÓNG ZALO
# ==================================================
st.set_page_config(
    page_title="Gia sư Hóa học THCS - THCS Phan Chu Trinh", 
    page_icon="🧪",
    layout="wide"
)

# 🚀 BỘ RENDER KATEX TỰ ĐỘNG - QUÉT MỌI ĐỊNH DẠNG TRONG HTML
st.components.v1.html("""
<script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('katex-css')) {
        const link = parentDoc.createElement('link');
        link.id = 'katex-css';
        link.rel = 'stylesheet';
        link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css';
        parentDoc.head.appendChild(link);
    }
    if (!parentDoc.getElementById('katex-js')) {
        const script = parentDoc.createElement('script');
        script.id = 'katex-js';
        script.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js';
        parentDoc.head.appendChild(script);
    }
    if (!parentDoc.getElementById('auto-render-js')) {
        const script2 = parentDoc.createElement('script');
        script2.id = 'auto-render-js';
        script2.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js';
        script2.onload = () => {
            setInterval(() => {
                if (window.parent.renderMathInElement) {
                    window.parent.renderMathInElement(window.parent.document.body, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false}
                        ],
                        throwOnError: false
                    });
                }
            }, 500);
        };
        parentDoc.head.appendChild(script2);
    }
</script>
""", height=0)

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

    /* -------------------------------------------------- */
    /* 💬 GIAO DIỆN ZALO CHUẨN MỰC */
    /* -------------------------------------------------- */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 18px;
        margin-bottom: 25px;
    }

    .chat-row-left {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 12px;
        max-width: 85%;
        margin-right: auto;
    }

    .chat-bubble-left {
        background-color: #ffffff;
        color: #0f172a;
        padding: 16px 22px;
        border-radius: 4px 20px 20px 20px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        font-size: 15px;
        line-height: 1.7;
    }

    .chat-bubble-left h3 {
        color: #0284c7;
        font-size: 17px;
        font-weight: 700;
        margin-top: 10px;
        margin-bottom: 6px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 4px;
    }

    .chat-bubble-left ul {
        margin: 6px 0;
        padding-left: 20px;
    }

    .chat-bubble-left li {
        margin-bottom: 4px;
    }

    .chat-row-right {
        display: flex;
        flex-direction: row-reverse;
        align-items: flex-start;
        gap: 12px;
        max-width: 80%;
        margin-left: auto;
    }

    .chat-bubble-right {
        background-color: #0284c7;
        color: #ffffff;
        padding: 14px 20px;
        border-radius: 20px 4px 20px 20px;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.22);
        font-size: 15px;
        line-height: 1.5;
        font-weight: 500;
    }

    .avatar-img {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0 3px 8px rgba(0,0,0,0.12);
        border: 2px solid #ffffff;
        flex-shrink: 0;
    }

    .katex {
        font-size: 1.15em !important;
    }

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

DEFAULT_TEACHER = "https://api.dicebear.com/7.x/bottts/svg?seed=Teacher"
DEFAULT_STUDENT = "https://api.dicebear.com/7.x/avataaars/svg?seed=Student"

AVATAR_TEACHER_SRC = TEACHER_B64 if TEACHER_B64 else DEFAULT_TEACHER
AVATAR_STUDENT_SRC = STUDENT_B64 if STUDENT_B64 else DEFAULT_STUDENT

# 🧪 HÀM ĐỊNH DẠNG TEXT (GỠ BỎ TOÀN BỘ REGEX PHÁ HOẠI $$)
def process_markdown_to_html(text):
    if not text:
        return ""
    
    # Sửa chuẩn mũi tên nhiệt độ cho KaTeX
    text = text.replace(r'\xrightarrow{t^\circ}', r'\xrightarrow{t^o}')
    text = text.replace(r'\xrightarrow{t^{\circ}}', r'\xrightarrow{t^o}')

    # Xử lý In đậm và Tiêu đề
    text = re.sub(r'(?m)^###\s*(.+)$', r'<h3>\1</h3>', text)
    text = re.sub(r'(?m)^\*\*([I|V|X\d]+\..+?)\*\*$', r'<h3>\1</h3>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # Xử lý Danh sách gạch đầu dòng an toàn
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                formatted_lines.append("<ul>")
                in_list = True
            formatted_lines.append(f"<li>{stripped[2:].strip()}</li>")
        else:
            if in_list:
                formatted_lines.append("</ul>")
                in_list = False
            formatted_lines.append(line)
            
    if in_list:
        formatted_lines.append("</ul>")
        
    result = "\n".join(formatted_lines)

    # Đổi \n thành <br> nhưng tuyệt đối KHÔNG đụng chạm vào $
    result = result.replace("\n\n", "<br><br>").replace("\n", "<br>")
    
    # Dọn dẹp khoảng trắng dư thừa HTML
    result = result.replace("<br><br><ul>", "<br><ul>").replace("</ul><br><br>", "</ul><br>")
    result = result.replace("<br><ul>", "<ul>").replace("</ul><br>", "</ul>")
    result = result.replace("<br><h3>", "<h3>").replace("</h3><br>", "</h3>")
    
    return result

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

# ==================================================
# 🔑 ÉP AI PHẢN HỒI ĐÚNG CHUẨN $$ TRÊN 1 DÒNG
# ==================================================
BASE_INSTRUCTION = r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Khoa học tự nhiên (phân môn Hóa học 8-9) tại trường THCS Phan Chu Trinh (Krông Búk).
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình GDPT 2018.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế (Oxygen, Aluminium, Hydrogen, Iron(III) oxide, Sulfate...).

# 📐 QUY TẮC LATEX (TUYỆT ĐỐI TUÂN THỦ)
1. Mỗi Phương trình hóa học phải ĐỨNG RIÊNG một dòng và BỌC KÍN trong `$$...$$`.
2. Tuyệt đối KHÔNG ngắt dòng (Enter) khi đang viết dở phương trình bên trong `$$`.
   - VÍ DỤ CHUẨN: $$2Al + 3Cl_2 \xrightarrow{t^o} 2AlCl_3$$
3. Các công thức hoặc kí hiệu ngắn kẹp trong `$`: $AlCl_3$, $m = n \times M$.
"""

ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của Thầy. Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác không?"

if has_rag_data:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n\nTÀI LIỆU:\n{knowledge_base_text}\n\n1. CHỈ TRẢ LỜI dựa trên tài liệu trên. 2. Nếu không có, trả về: {ERROR_MESSAGE_TAG}"""
else:
    SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n- Trả lời bằng tri thức Hóa học THCS. Nếu không liên quan, trả về: {ERROR_MESSAGE_TAG}"""

if client:
    try:
        chat_session = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2 if has_rag_data else 0.3
            )
        )
    except Exception as e:
        st.error(f"Lỗi khởi tạo chat session: {e}")

# ==================================================
# 📌 THANH BÊN TRÁI & GIAO DIỆN
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

# 📍 BANNER
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

# 📍 KHUNG CHAT
chat_placeholder = st.container()

def render_chat_html(role, content):
    if role == "assistant":
        html_content = process_markdown_to_html(content)
        return f"""<div class="chat-row-left"><img src="{AVATAR_TEACHER_SRC}" class="avatar-img" /><div class="chat-bubble-left">{html_content}</div></div>"""
    else:
        formatted_user_text = content.replace("\n", "<br>")
        return f"""<div class="chat-row-right"><img src="{AVATAR_STUDENT_SRC}" class="avatar-img" /><div class="chat-bubble-right">{formatted_user_text}</div></div>"""

with chat_placeholder:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        st.markdown(render_chat_html(msg["role"], msg["content"]), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 📍 NHẬP LIỆU
uploaded_file = st.file_uploader("📷 Chụp hoặc gửi ảnh", type=["jpg", "jpeg", "png"], key="uploader")
prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào...")

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
        st.markdown(render_chat_html("user", cleaned_prompt), unsafe_allow_html=True)

        with st.spinner("Thầy đang xem bài..."):
            try:
                message_parts.append(types.Part.from_text(text=cleaned_prompt))
                response = chat_session.send_message(message_parts)
                res_text = response.text.strip()
                
                if ERROR_MESSAGE_TAG.upper() in res_text.upper():
                    if cleaned_prompt not in st.session_state.missing_questions:
                        st.session_state.missing_questions.append(cleaned_prompt)
                        save_data(STORAGE_FILE, st.session_state.missing_questions)
                    final_res = ERROR_MESSAGE
                else:
                    final_res = res_text

                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_data(HISTORY_FILE, st.session_state.messages)
                st.rerun()
            except Exception as e:
                st.error(f"Thầy gặp sự cố kết nối: {e}")
