import os
import json
import base64
import re
import streamlit as st
from google import genai
from google.genai import types

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

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

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "chat_history.json")
STORAGE_FILE = os.path.join(CURRENT_DIR, "missing_questions.json")
PASSWORD_KEY = "CLEAR_PASSWORD"

def get_image_base64(base_name):
    for ext in [".PNG", ".png", ".jpg", ".jpeg", ".JPG", ".JPEG"]:
        path = os.path.join(CURRENT_DIR, f"{base_name}{ext}")
        if os.path.exists(path):
            try:
                with open(path, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode()
                    ext_type = "png" if "png" in ext.lower() else "jpeg"
                    return f"data:image/{ext_type};base64,{encoded}"
            except:
                pass
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

if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
        os.environ["GOOGLE_API_KEY"] = api_key
    except Exception as e:
        st.error(f"Lỗi kết nối Gemini API: {e}")

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

@st.cache_resource(show_spinner="Đang nạp dữ liệu trí tuệ nhân tạo...")
def init_vector_db():
    db_path = os.path.join(CURRENT_DIR, "faiss_db_luu_tru") 
    if not os.path.exists(db_path):
        return None, f"Không tìm thấy thư mục {db_path}"
        
    try:
        embeddings = ModernGeminiEmbeddings(api_key=api_key)
        vectorstore = FAISS.load_local(
            folder_path=db_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        return vectorstore, "OK"
    except Exception as e:
        return None, str(e)

db, db_error = init_vector_db()
has_rag_data = db is not None

BASE_INSTRUCTION = r"""
# VAI TRÒ & NGUYÊN TẮC
- Bạn là "Gia sư ảo" môn Hóa học THCS (GDPT 2018) tại trường THCS Phan Chu Trinh (Krông Búk).
- Xưng "Thầy", gọi "Em". Phong cách gần gũi, khích lệ, sư phạm, tuyệt đối không giải thay hoàn toàn.
- PHẠM VI: Chỉ dùng kiến thức Hóa học cấp THCS (GDPT 2018). Dùng 100% tên quốc tế (IUPAC).
- ĐIỀU KIỆN CHUẨN (ĐKC): Thể tích mol chất khí mặc định là $24,79 \text{ L/mol}$ (trừ khi đề yêu cầu đktc dùng $22,4 \text{ L/mol}$).

# CHIẾN LƯỢC SƯ PHẠM & XỬ LÝ CÂU HỎI CHUNG CHUNG
1. **QUY TẮC CHO CÂU HỎI CHUNG CHUNG (CỰC KỲ QUAN TRỌNG):** Khi học sinh hỏi một vấn đề quá rộng, mơ hồ, không rõ trọng tâm (ví dụ chỉ hỏi "Kim loại", "Acid là gì", "Phi kim"... mà không chỉ rõ tính chất hóa học hay bài tập cụ thể):
   - **TUYỆT ĐỐI KHÔNG** tuôn ra một tràng kiến thức dài dặc làm học sinh ngợp.
   - **HÃY TÓM TẮT THÀNH MENU NGẮN GỌN:** Liệt kê các nội dung chính của chủ đề đó và hỏi xem học sinh muốn tìm hiểu phần nào trước. 
   - *Ví dụ mẫu:* "Em hỏi khái quát quá! Về phần Kim loại, chúng ta sẽ tìm hiểu qua các mục chính sau: 1. Tính chất vật lý, 2. Tính chất hóa học, 3. Dãy hoạt động hóa học, 4. Ứng dụng và sản xuất. Em muốn thầy trò mình bắt đầu khám phá phần nào trước nào?"
2. **CÂU HỎI LÝ THUYẾT CỤ THỂ:** Trả lời trực tiếp, rõ ràng, đủ ý, không ngắt quãng.
3. **CÂU HỎI BÀI TẬP:** Bắt buộc đưa ra 3 lựa chọn cho học sinh (A: Cùng giải, B: Gợi ý từng bước, C: Đáp án chi tiết hoàn chỉnh không kèm hướng dẫn). Bài giải chi tiết tuyệt đối không có các bước hoặc hướng dẫn.
4. Không sa đà vào các bước giải toán học trung gian (như giải hệ phương trình chỉ cần ghi ra hệ pt rồi cho đáp án luôn).

# TRÌNH BÀY (ĐẸP NHƯ VIẾT BẢNG)
- Có dòng trống giữa các đoạn văn.
- Đề mục **IN ĐẬM** và đứng riêng một dòng.
- Phương trình và công thức hóa học bọc trong $$...$$ (riêng dòng) hoặc $...$ (cùng dòng).
- Kết thúc bằng một câu hỏi gợi mở.
"""
OUT_OF_CONTEXT_TAG = "[THIEU_DATA]"

with st.sidebar:
    sidebar_img_loaded = False
    for ext in [".png", ".PNG", ".jpg", ".jpeg", ".JPG"]:
        sidebar_img_path = os.path.join(CURRENT_DIR, f"sidebar_logo{ext}")
        if os.path.exists(sidebar_img_path):
            try:
                st.image(sidebar_img_path, use_container_width=True)
                sidebar_img_loaded = True
                break
            except Exception:
                pass
            
    if not sidebar_img_loaded:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 1.2rem 1rem; border-radius: 14px; color: white; text-align: center; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);">
            <div style="font-size: 2.2rem; margin-bottom: 4px;">🧪</div>
            <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #ffffff !important; letter-spacing: 0.5px;">LỚP HÓA HỌC THCS</h3>
            <p style="margin: 4px 0 0 0; font-size: 0.82rem; opacity: 0.9; color: #e0f2fe !important; font-weight: 500;">Trường THCS Phan Chu Trinh - Krông Búk</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()

    # HIỂN THỊ CẢ ẢNH ICON VÀ DÒNG TRẠNG THÁI CHUẨN XÁC
    icon_tailieu_loaded = False
    for ext in [".png", ".PNG", ".jpg", ".jpeg", ".JPG"]:
        icon_path = os.path.join(CURRENT_DIR, f"icon_tailieudaketnoi{ext}")
        if os.path.exists(icon_path):
            try:
                st.image(icon_path, use_container_width=True)
                icon_tailieu_loaded = True
                break
            except Exception:
                pass
            
    if has_rag_data:
        st.success("**Đang sử dụng:** Học liệu chuẩn do Giáo viên biên soạn")
    else:
        st.info("**Đang sử dụng:** Tri thức nền tảng của Mô hình ngôn ngữ (LLM)")

    st.divider()

    banner_kt_loaded = False
    for ext in [".png", ".PNG", ".jpg", ".jpeg", ".JPG"]:
        banner_kt_path = os.path.join(CURRENT_DIR, f"kien_thuc_can_bo_sung{ext}")
        if os.path.exists(banner_kt_path):
            try:
                st.image(banner_kt_path, use_container_width=True)
                banner_kt_loaded = True
                break
            except Exception:
                pass
            
    if not banner_kt_loaded:
        st.header("📝 Câu hỏi Cần Bổ Sung")

    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions, 1):
            st.markdown(f"**{i}.** {q}")
        with st.form("clear_form"):
            password = st.text_input("Mật khẩu để xóa", type="password")
            if st.form_submit_button("Xóa Toàn bộ"):
                correct_pass = st.secrets.get(PASSWORD_KEY)
                if password == correct_pass:
                    st.session_state.missing_questions = []
                    save_data(STORAGE_FILE, [])
                    st.success("✅ Đã xóa thành công!")
                    st.rerun()
                else: 
                    st.error("❌ Mật khẩu không chính xác.")
    else:
        st.write("Không có câu hỏi nào.")

    st.divider()
    if st.button("🗑️ Xóa lịch sử", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        save_data(HISTORY_FILE, st.session_state.messages)
        st.rerun()

banner_loaded = False
for name in ["banner.png", "banner.PNG", "banner.jpg", "banner.jpeg", "banner.JPG"]:
    banner_path = os.path.join(CURRENT_DIR, name)
    if os.path.exists(banner_path):
        try:
            st.image(banner_path, use_container_width=True)
            banner_loaded = True
            break
        except Exception:
            pass
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
        if st.button("✨ XOÁ LỊCH SỬ CHAT THƯỜNG XUYÊN GIÚP HỆ THỐNG CHẠY MƯỢT MÀ HƠN - BẤM VÀO ĐÂY NÈ ✨", type="primary", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
            save_data(HISTORY_FILE, st.session_state.messages)
            st.rerun()

st.markdown("<br><br><br>", unsafe_allow_html=True)

# ĐÃ LOẠI BỎ ĐỊNH DẠNG DOC, DOCX KHỎI FILE UPLOADER
uploaded_file = st.file_uploader(
    "📎 Tải lên tệp hoặc ảnh (Ảnh, PDF, TXT)", 
    type=["jpg", "jpeg", "png", "pdf", "txt"], 
    key=f"uploader_{st.session_state.file_uploader_key}"
)

prompt = st.chat_input("Em muốn hỏi Thầy bài tập hay lý thuyết Hóa học nào...")

if prompt:
    if not client: st.stop()
    cleaned_prompt = prompt.strip()
    
    user_msg_content = cleaned_prompt
    
    if uploaded_file: 
        user_msg_content = f"📎 (Kèm tệp: {uploaded_file.name}) {cleaned_prompt}"

    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    save_data(HISTORY_FILE, st.session_state.messages)
    render_zalo_chat("user", cleaned_prompt)

    with st.chat_message("assistant", avatar=AVATAR_TEACHER_SRC):
        st.markdown("<span class='assistant-anchor'></span>", unsafe_allow_html=True)
        with st.spinner("Thầy đang xem bài..."):
            try:
                gemini_history = []
                recent_messages = st.session_state.messages[:-1][-6:]
                
                for msg in recent_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                
                message_parts = []
                
                if uploaded_file:
                    mime_type = uploaded_file.type
                    if not mime_type:
                        if uploaded_file.name.endswith(".pdf"): mime_type = "application/pdf"
                        elif uploaded_file.name.endswith(".txt"): mime_type = "text/plain"
                    
                    message_parts.append(types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=mime_type))
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))
                else:
                    message_parts.append(types.Part.from_text(text=cleaned_prompt))

                gemini_history.append(types.Content(role="user", parts=message_parts))

                if has_rag_data:
                    docs_lien_quan = db.similarity_search(cleaned_prompt, k=2)
                    nguon_kien_thuc = "\n\n".join([doc.page_content for doc in docs_lien_quan])
                    DYNAMIC_SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
                    
=== TÀI LIỆU CỦA THẦY ===
{nguon_kien_thuc}

=== YÊU CẦU QUAN TRỌNG ===
1. Ưu tiên cao nhất sử dụng TÀI LIỆU CỦA THẦY để trả lời.
2. KHI ĐỌC ĐỀ BÀI TỪ TỆP HOẶC TÀI LIỆU: Bắt buộc phải trích xuất NGUYÊN VĂN, CHÍNH XÁC TỪNG CHỮ, TỪNG CON SỐ của câu hỏi được yêu cầu. Tuyệt đối không tự ý thay đổi số liệu, không gộp dữ kiện của câu này vào câu khác.
3. Nếu thông tin trong tài liệu KHÔNG ĐỦ hoặc KHÔNG CÓ để trả lời, bạn VẪN PHẢI TRẢ LỜI học sinh bằng tri thức nền của bạn (nhưng phải kiểm soát chặt chẽ để đảm bảo chuẩn kiến thức THCS GDPT 2018).
4. LỆNH BẮT BUỘC: Nếu bạn phải dùng tri thức nền (bên ngoài tài liệu) để trả lời dù chỉ một phần nhỏ, bạn PHẢI chèn thêm đúng chuỗi ký tự {OUT_OF_CONTEXT_TAG} vào cuối cùng của câu trả lời."""
                else:
                    DYNAMIC_SYSTEM_INSTRUCTION = f"""{BASE_INSTRUCTION}
                    
=== YÊU CẦU QUAN TRỌNG ===
1. Trả lời học sinh bằng tri thức Hóa học chuẩn THCS (GDPT 2018).
2. KHI ĐỌC ĐỀ BÀI TỪ TỆP: Bắt buộc phải trích xuất NGUYÊN VĂN, CHÍNH XÁC TỪNG CHỮ, TỪNG CON SỐ của câu hỏi được yêu cầu. Tuyệt đối không tự ý thay đổi số liệu, không gộp dữ kiện của câu này vào câu khác.
3. LỆNH BẮT BUỘC: Bạn PHẢI chèn thêm đúng chuỗi ký tự {OUT_OF_CONTEXT_TAG} vào cuối cùng của câu trả lời."""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=DYNAMIC_SYSTEM_INSTRUCTION,
                        temperature=0.3
                    )
                )
                res_text = response.text.strip()
                
                if OUT_OF_CONTEXT_TAG in res_text:
                    if cleaned_prompt not in st.session_state.missing_questions:
                        st.session_state.missing_questions.append(cleaned_prompt)
                        save_data(STORAGE_FILE, st.session_state.missing_questions)

                    final_res = res_text.replace(OUT_OF_CONTEXT_TAG, "").strip()
                else:
                    final_res = res_text

                st.session_state.messages.append({"role": "assistant", "content": final_res})
                save_data(HISTORY_FILE, st.session_state.messages)
                
                st.session_state.file_uploader_key += 1
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Thầy gặp sự cố kết nối: {e}")
