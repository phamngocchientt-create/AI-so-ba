import streamlit as st
from google import genai
from google.genai import types
import os
import json 
import time

# ==================================================
# 📌 1. CẤU HÌNH HỆ THỐNG & FILE LƯU TRỮ
# ==================================================
STORAGE_FILE = "missing_questions.json"
HISTORY_FILE = "chat_history.json" 
ERROR_MESSAGE_TAG = "[MISSING_DOC]"
ERROR_MESSAGE = f"Xin lỗi em, thông tin này hiện chưa có trong thư viện tài liệu của thầy. {ERROR_MESSAGE_TAG} Thầy sẽ sớm cập nhật kiến thức này nhanh nhất có thể."
HARDCODED_GREETING = "Xin chào em, thầy là Gia sư Hoá học trường Phan Chu Trinh. Thầy đã sẵn sàng đồng hành cùng em rồi đây!"

def load_data(file_path, default_value):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default_value
    return default_value

def save_data(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# ==================================================
# 📌 2. KHỞI TẠO GIAO DIỆN (LUÔN HIỆN KHUNG CHAT)
# ==================================================
st.set_page_config(page_title="Gia sư Hóa học THCS", layout="wide")
st.title("👨‍🔬 Gia sư Hóa học THCS - Trường Phan Chu Trinh")

if "messages" not in st.session_state:
    st.session_state.messages = load_data(HISTORY_FILE, [{"role": "assistant", "content": HARDCODED_GREETING}])
if "missing_questions" not in st.session_state:
    st.session_state.missing_questions = load_data(STORAGE_FILE, [])

# ==================================================
# ⚙️ 3. CẤU HÌNH CHAT SESSION (BẢN FIX TRIỆT ĐỂ 404/400)
# ==================================================
@st.cache_resource
def setup_chat_session():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, None, 0

    # Khởi tạo Client mặc định để SDK tự chọn phiên bản ổn định nhất
    client = genai.Client(api_key=api_key)
    
    # Quét tri thức từ thư mục 'files'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(current_dir, "files")
    knowledge_base = ""
    if os.path.exists(files_dir):
        for filename in os.listdir(files_dir):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join(files_dir, filename), "r", encoding="utf-8") as f:
                        knowledge_base += f"\n\n--- DỮ LIỆU TỪ FILE {filename} ---\n" + f.read()
                except: pass

    # --- NỘI DUNG PROMPT ENGINEERING CỦA THẦY ---
    sys_instruct = (r"""
# 🚨 QUY TẮC HIỂN THỊ (BẮT BUỘC)
1. TUYỆT ĐỐI KHÔNG hiển thị các thẻ XML như <co_ban>, <huong_dan_giai>, <bai_giai_chi_tiet> ra màn hình.
2. BẠN LÀ THẦY GIÁO, KHÔNG PHẢI MÁY TRÍCH XUẤT. Hãy diễn đạt lại kiến thức bằng ngôn ngữ giảng bài tự nhiên, đẹp mắt qua Markdown và LaTeX.
3. Chỉ dùng kiến thức trong "KHO TRI THỨC" bên dưới. Nếu thiếu, báo [MISSING_DOC].

# 🎭 VAI TRÒ & DANH TÍNH
Bạn là "Gia sư ảo" chuyên phân môn Hóa học THCS, hoạt động theo kiến thức chương trình GDPT 2018, lưu ý hãy sử dụng danh pháp quốc tế theo chương trình GDPT 2018. 
- Phong cách: Một thầy giáo tâm huyết, xưng "Thầy", gọi "Em". 
- Ngôn ngữ: Gần gũi, khích lệ nhưng khoa học, đúng chuẩn sư phạm trường Phan Chu Trinh.
- Mục tiêu: Không dạy thay, chỉ dẫn dắt để học sinh tự tìm ra ánh sáng tri thức.
Hoạt động theo chương trình GDPT 2018, sử dụng danh pháp quốc tế (Aluminium, Oxide...).

# 🎓 CHIẾN LƯỢC SƯ PHẠM (SCAFFOLDING)
Nếu học sinh hỏi lí thuyết, hãy trả lời ngay, sử dụng kiến thức cơ bản để trả lời. Chỉ khi học sinh muốn hiểu sâu hơn, kiểu như giải thích thì mới dùng kiến thức giải thích để trả lời. Khi học sinh cần kiến thức nâng cao mới dùng kiến thức nâng cao trả lời
Khi học sinh hỏi bài tập: (cả bài tập tính toán và lí thuyết): hãy hỏi học sinh muốn được hướng dẫn hay nhận luôn bài giải chi tiết, khuyến khích học sinh nên tập giải bài theo hướng dẫn để hiểu bài hơn.


# 📐 QUY TẮC LATEX
- Công thức: bọc trong $...$ hoặc $$...$$.
- Khi đưa ra câu trả lời hãy đưa ra dưới hình thức thật chỉn chu, đẹp mắt, đừng để các PTHH dính vào nhau, các phần đề mục như I, II, III,... a, b, c, ...,   1, 2, 3,... phải đứng riền và được in đậm
    """)

    full_instruction = sys_instruct + "\n\n# 📚 KHO TRI THỨC ĐƯỢC NẠP:\n" + knowledge_base

    try:
        # Dùng Gemini 2.0 Flash bản chuẩn nhất 2026
        chat = client.chats.create(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(system_instruction=full_instruction, temperature=0.0)
        )
        return client, chat, len(knowledge_base)
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối AI: {e}")
        return None, None, 0

client, chat_session, total_chars = setup_chat_session() 

# ==================================================
# 🎨 4. SIDEBAR & GIAO DIỆN HIỂN THỊ
# ==================================================
with st.sidebar:
    if total_chars > 0:
        st.success(f"✅ Đã nạp {total_chars} ký tự tri thức.")
    else:
        st.error("❌ Không tìm thấy tài liệu (.txt) trong thư mục 'files'.")

    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.messages = [{"role": "assistant", "content": HARDCODED_GREETING}]
        if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
        st.rerun()

    st.markdown("---")
    st.header("📝 Câu hỏi Cần Bổ Sung")
    if st.session_state.missing_questions:
        for i, q in enumerate(st.session_state.missing_questions):
            st.markdown(f"**{i+1}.** {q}")

# Hiển thị lịch sử Chat
chat_placeholder = st.container()
with chat_placeholder:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

st.markdown("---")
# Khung nhập liệu (Luôn luôn hiện ở dưới cùng)
uploaded_file = st.file_uploader("📷 Gửi ảnh đề bài", type=["jpg", "jpeg", "png"], key="file_up")
prompt = st.chat_input("Nhập câu hỏi cho thầy...")

# ==================================================
# 🚀 5. XỬ LÝ LOGIC (CHỐNG LỖI 429 BẰNG RETRY)
# ==================================================
if prompt:
    if not client:
        st.error("⚠️ AI chưa khởi động. Thầy kiểm tra lại API Key nhé!")
    else:
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
                        time.sleep(1) # Nghỉ để tránh lỗi 429
                        message_parts.append(types.Part.from_text(text=cleaned_prompt))
                        
                        response = None
                        # Cơ chế tự động thử lại 3 lần nếu Google báo bận
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
                        
                        # Chặn hiển thị thẻ XML
                        if ERROR_MESSAGE_TAG in res_text or "[MISSING_DOC]" in res_text:
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
                        st.error(f"Hệ thống bận một chút, em đợi 10 giây rồi thử lại nhé! (Lỗi: {e})")
