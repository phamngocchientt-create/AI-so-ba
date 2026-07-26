import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

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
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }
    .stApp { background-color: #f1f5f9; }

    [data-testid="stChatMessage"] { background-color: transparent !important; border: none !important; padding: 0 !important; margin-bottom: 24px !important; gap: 12px !important; }
    [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] { width: 44px !important; height: 44px !important; border-radius: 50% !important; border: 2px solid #ffffff !important; box-shadow: 0 3px 8px rgba(0,0,0,0.12) !important; background-color: #fff !important; }
    
    [data-testid="stChatMessage"]:has(.user-anchor) { flex-direction: row-reverse !important; }
    [data-testid="stChatMessage"]:has(.user-anchor) [data-testid="stChatMessageContent"] { background-color: #0068ff !important; color: #ffffff !important; border-radius: 20px 4px 20px 20px !important; box-shadow: 0 4px 12px rgba(0, 104, 255, 0.22) !important; padding: 12px 20px !important; max-width: 80% !important; }
    [data-testid="stChatMessage"]:has(.user-anchor) [data-testid="stChatMessageContent"] * { color: #ffffff !important; }

    [data-testid="stChatMessage"]:has(.assistant-anchor) { flex-direction: row !important; }
    [data-testid="stChatMessage"]:has(.assistant-anchor) [data-testid="stChatMessageContent"] { background-color: #ffffff !important; color: #0f172a !important; border-radius: 4px 20px 20px 20px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05) !important; padding: 16px 24px !important; max-width: 85% !important; line-height: 1.6 !important; }
    [data-testid="stChatMessage"]:has(.assistant-anchor) [data-testid="stChatMessageContent"] h3 { color: #0284c7 !important; font-size: 1.1em !important; border-bottom: 2px solid #f1f5f9; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; }

    .katex { font-size: 1.12em !important; }

    [data-testid="stChatInput"] { border-radius: 30px !important; border: 2px solid #38bdf8 !important; background-color: #ffffff !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15) !important; padding: 4px 8px !important; }
    [data-testid="stChatInput"]:focus-within { border-color: #0284c7 !important; }
    [data-testid="stChatInputSubmitButton"] { background-color: #0284c7 !important; color: white !important; border-radius: 50% !important; }
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

def process_ai_response(text):
    if not text: return ""
    text = text.replace(r'\xrightarrow{t^\circ}', r'\xrightarrow{t^o}')
    text = text.replace(r'\xrightarrow{t^{\circ}}', r'\xrightarrow{t^o}')
    text = re.sub(r'(?<!\$)\$([^$]+?(?:\\rightarrow|\\longrightarrow|\\xrightarrow)[^$]+?)\$(?!\$)', r'$$\1$$', text)
    text = re.sub(r'\s*\$\$\s*', r'\n$$\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return default_value
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

HARDCODED_GREETING = "Xin chào em! Thầy là Gia sư Hóa học THCS. Em đang gặp khó khăn ở bài tập hay lý thuyết Hóa học nào, cứ chia sẻ với Thầy nhé!"

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
        os.environ["GOOGLE_API_KEY"] = api_key
    except Exception as e:
        st.error(f"Lỗi kết nối Gemini API: {e}")

# ==================================================
# 🚀 CHUẨN MỚI 2026: SỬ DỤNG GEMINI-EMBEDDING-001
# ==================================================
class ModernGeminiEmbeddings(Embeddings):
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        
    def embed_documents(self, texts):
        all_embeddings = []
        for text in texts:
            res = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=text
            )
            all_embeddings.append(res.embeddings[0].values)
        return all_embeddings
        
    def embed_query(self, text):
        res = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return res.embeddings[0].values

@st.cache_resource(show_spinner="Đang hệ thống hóa tài liệu môn KHTN...")
def init_vector_db():
    doc_path = os.path.join(CURRENT_DIR, "tai_lieu_hoa.txt")
    if not os.path.exists(doc_path):
        return None, "Không tìm thấy file tai_lieu_hoa.txt"
    try:
        loader = TextLoader(doc_path, encoding='utf-8')
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        splits = text_splitter.split_documents(documents)
        
        # Gọi chính xác mô hình thế hệ mới
        embeddings = ModernGeminiEmbeddings(api_key=api_key)
        vectorstore = FAISS.from_documents(splits, embeddings)
        return vectorstore, "OK"
    except Exception as e:
        return None, str(e)

db, db_error = init_vector_db()

# Đọc kiểu cũ để DỰ PHÒNG 
knowledge_base_text = ""
try:
    with open(os.path.join(CURRENT_DIR, "tai_lieu_hoa.txt"), "r", encoding="utf-8") as f:
        knowledge_base_text = f.read().strip()
except:
    pass

has_rag_data = db is not None
has_fallback_data = bool(knowledge_base_text)

# ==================================================
# 🔑 SYSTEM INSTRUCTION
# ==================================================
BASE_INSTRUCTION = r"""
# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên trách môn Khoa học tự nhiên (phân môn Hóa học khối 8-9) tại trường THCS Phan Chu Trinh (xã Krông Búk).
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em".
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm.
- Mục tiêu: Không chủ động giải thay, ưu tiên dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.

# 📖 CHUẨN CHUYÊN MÔN GDPT 2018 (BẮT BUỘC)
1. PHẠM VI: Chỉ sử dụng kiến thức trong chương trình GDPT 2018 cấp THCS (phân môn Hóa học). Tuyệt đối không đưa kiến thức THPT/Đại học vào bài giảng.
2. DANH PHÁP (IUPAC): Sử dụng 100% tên quốc tế. Hoặc theo quy định của chương trình GDPT 2018.
3. ĐIỀU KIỆN CHUẨN (ĐKC): Đây là chuẩn mặc định. Thể tích mol chất khí là $24,79 \text{ L/mol}$. Lưu ý vẫn nếu đề bài hoặc học sinh yêu cầu về điều kiện tiêu chuẩn (đktc) thì vẫn sử dụng thể tích mol chất khí là$22,4 \text{ L/mol}$

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
1. CÂU HỎI LÝ THUYẾT: Trả lời trực tiếp, rõ ràng. Chỉ dùng kiến thức cơ bản trừ khi HS hỏi sâu.
2. CÂU HỎI BÀI TẬP: Đưa ra 3 lựa chọn (A: Cùng giải, B: Gợi ý bước, C: Đáp án chi tiết).
Nếu HS chọn C, dùng kiến thức cung cấp và kết hợp với kiến thức nền của AI nếu tài liệu bị thiếu kiến thức phần đó để giải đầy đủ. Bài giải chi tiết cung cấp cho học sinh là bài hoàn chỉnh không ghi các bước, hoặc đưa chỉ dẫn, hướng dẫn vào trong bài nữa
Để câu trả lời đẹp như "viết bảng", PHẢI tuân thủ:
1. KHOẢNG TRẮNG: Dòng trống giữa các đoạn văn.
2. ĐỀ MỤC: IN ĐẬM và đứng riêng một dòng.
3. PHƯƠNG TRÌNH HÓA HỌC: Bọc trong $$...$$ riêng dòng.
4. CÔNG THỨC & LATEX: Bọc trong $...$ (cùng dòng) hoặc $$...$$ (riêng dòng).

# ❤️ PHONG CÁCH
- Khích lệ tinh thần tự giác của các em.
- Kết thúc bằng một câu hỏi gợi mở.
"""
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của Thầy. Thầy sẽ sớm cập nhật kiến thức này. {ERROR_MESSAGE_TAG} Em có thể hỏi về một chủ đề khác không?"

# ==================================================
# 📌 THANH BÊN TRÁI (SIDEBAR)
# ==================================================
with st.sidebar:
    st.title("🧪 Lớp Hóa Học THCS")
    st.caption("Trường THCS Phan Chu Trinh - Krông Búk")
    st.divider()

    if has_rag_data:
        st.success("📚 **Đang dùng:** Tài liệu Vector DB (Tối ưu chi phí & Bám sát giáo án)")
    elif has_fallback_data:
        st.warning("⚠️ **Đang dùng:** Tài liệu Cũ (Bám sát giáo án, nhưng tốn phí). Hệ thống Vector đang lỗi.")
        st.error(f"Chi tiết lỗi: {db_error}")
    else:
        st.error("⚡ **Đang dùng:** Tri thức mở (Cảnh báo: Không có tài liệu!)")

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

def render_zalo_chat(role, content):
    if role == "user":
        avatar_src = AVATAR_STUDENT_SRC
        anchor = "<span class='user-anchor'></span>"
    else:
        avatar_src = AVATAR_TEACHER_SRC
        anchor = "<span class='assistant-anchor'></span>"
        content = process_ai_response(content)
        
    with st.chat_message(role, avatar=avatar_src):
        st.markdown(f"{anchor}\n{content}", unsafe_allow_html=True)

for msg in st.session_state.messages:
    render_zalo_chat(msg["role"], msg["content"])

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
<style>
    button[kind="primary"] { background: linear-gradient(135deg, #ff007f 0%, #ff5e00 100%) !important; border: none !important; border-radius: 40px !important; box-shadow: 0 5px 15px rgba(255, 94, 0, 0.4) !important; padding: 10px 20px !important; transition: all 0.3s ease-in-out !important; }
    button[kind="primary"]:hover { transform: scale(1.02) !important; box-shadow: 0 8px 25px rgba(255, 94, 0, 0.6) !important; }
    button[kind="primary"] p { color: #ffffff !important; font-size: 1.15rem !important; font-weight: 800 !important; text-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important; margin: 0 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; }
</style>
""", unsafe_allow_html=True)

if len(st.session_state.messages) > 1:
    col1, col2, col3 = st.columns([0.2, 9.6, 0.2])
    with col2:
        if st.button("✨ XOÁ LỊCH SỬ CHAT THƯỜNG XUYÊN ĐỂ CHẠY MƯỢT MÀ NHÉ CÁC EM, BẤM VÀO ĐỂ XOÁ NÈ ✨", type="primary", use_container_width=True):
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
    
    user_msg_content = cleaned_prompt
    if uploaded_file: user_msg_content = f"📝 (Kèm ảnh) {cleaned_prompt}"

    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)
    render_zalo_chat("user", cleaned_prompt)

    with st.chat_message("assistant", avatar=AVATAR_TEACHER_SRC):
        st.markdown("<span class='assistant-anchor'></span>", unsafe_allow_html=True)
        with st.spinner("Thầy đang xem bài..."):
            try:
                gemini_history = []
                for msg in st.session_state.messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                
                message_parts = []
                if uploaded_file: message_parts.append(types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
                message_parts.append(types.Part.from_text(text=cleaned_prompt))
                gemini_history.append(types.Content(role="user", parts=message_parts))

                if has_rag_data:
                    docs_lien_quan = db.similarity_search(cleaned_prompt, k=3)
                    nguon_kien_thuc = "\n\n".join([doc.page_content for doc in docs_lien_quan])
                    DYNAMIC_SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n\nTÀI LIỆU CỦA THẦY TRÍCH XUẤT:\n{nguon_kien_thuc}\n\n1. CHỈ TRẢ LỜI dựa trên tài liệu. 2. Nếu không có, trả về: {ERROR_MESSAGE_TAG}"""
                elif has_fallback_data:
                    DYNAMIC_SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n\nTÀI LIỆU CỦA THẦY:\n{knowledge_base_text}\n\n1. CHỈ TRẢ LỜI dựa trên tài liệu. 2. Nếu không có, trả về: {ERROR_MESSAGE_TAG}"""
                else:
                    DYNAMIC_SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}\n- Trả lời bằng tri thức Hóa học. Nếu ngoài phạm vi, trả về: {ERROR_MESSAGE_TAG}"""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=DYNAMIC_SYSTEM_INSTRUCTION,
                        temperature=0.2 if (has_rag_data or has_fallback_data) else 0.3
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

                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_data(HISTORY_FILE, st.session_state.messages)
                st.rerun()
                
            except Exception as e:
                st.error(f"Thầy gặp sự cố kết nối: {e}")
