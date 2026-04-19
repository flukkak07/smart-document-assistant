import sys
import os
import time
import tempfile
from typing import List, Any

# เพิ่ม root path ให้ Python หา src/ เจอ (จำเป็นเมื่อรัน streamlit จาก root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(
    page_title="GraphRAG AI Assistant",
    page_icon="https://img.icons8.com/color/48/brain.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# บังคับ scroll กลับไปที่บนสุดทุกครั้งที่ Streamlit rerun
# ต้องใช้ window.parent เพราะ Streamlit render widgets ผ่าน iframe
st.markdown(
    "<script>window.parent.document.querySelector('.main').scrollTo(0, 0);</script>",
    unsafe_allow_html=True,
)

# โหลด Font Awesome และ Google Fonts แบบ link tag (เสถียรกว่า @import ใน Streamlit)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

# Custom CSS ส่วนที่เหลือ (ไม่มี @import แล้ว)
custom_css = """
<style>
    /* ไม่ใช้ [class*="st-"] เพื่อไม่ให้ฟอนต์ไปทับไอคอน Material ของระบบ */
    html, body, p, div, h1, h2, h3, h4, h5, h6, span, li, button, input {
        font-family: 'Sarabun', sans-serif;
    }
    /* ป้องกันการเปลี่ยนฟอนต์ของไอคอน Streamlit */
    .material-symbols-rounded, .material-icons {
        font-family: 'Material Symbols Rounded', sans-serif !important;
    }

    /* ไม่ต้องซ่อน Header เพื่อให้ปุ่ม Sidebar ยังแสดงปกติ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}


    /* พื้นหลังแอป */
    .stApp {
        background: linear-gradient(160deg, #0f172a 0%, #1e293b 60%, #0f2a2a 100%);
        color: #f1f5f9;
    }

    /* ระยะห่างพื้นที่หลัก */
    .main > div { padding: 2rem 2.5rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1a2540 100%);
        border-right: 1px solid #1e3a5f;
    }

    /* หัวข้อด้วยไอคอน */
    .page-title {
        font-size: 2rem;
        font-weight: 700;
        color: #f1f5f9;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }
    .page-title i { color: #0d9488; }

    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 1rem 0 0.5rem 0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .section-header i { color: #0d9488; }

    .sidebar-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f1f5f9;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .sidebar-title i { color: #0d9488; }

    /* กล่องสถานะ */
    .status-card {
        border-radius: 10px;
        padding: 8px 14px;
        margin: 5px 0;
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-ok {
        background: rgba(13, 148, 136, 0.15);
        border: 1px solid #0d9488;
        color: #5eead4;
    }
    .status-warn {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid #f59e0b;
        color: #fcd34d;
    }

    /* ปุ่ม Start Indexing */
    .st-key-btn_indexing > button {
        background: linear-gradient(90deg, #059669, #0d9488) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .st-key-btn_indexing > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(13,148,136,0.4) !important;
    }

    /* Welcome Card */
    .welcome-card {
        background: linear-gradient(135deg, rgba(13, 148, 136, 0.08), rgba(30, 58, 95, 0.15));
        border: 1px solid rgba(13, 148, 136, 0.3);
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 3rem auto;
        max-width: 560px;
    }
    .welcome-card .big-icon {
        font-size: 3.5rem;
        color: #0d9488;
        margin-bottom: 1rem;
    }
    .welcome-card h2 { color: #f1f5f9; margin-bottom: 0.5rem; }
    .welcome-card p  { color: #94a3b8; line-height: 1.8; }
    .flow-steps {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: #64748b;
    }
    .flow-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        color: #94a3b8;
    }
    .flow-step i { font-size: 1.6rem; color: #0d9488; }
    .flow-arrow { color: #334155; font-size: 1.4rem; }

    /* Label ชื่อผู้ส่ง (เหมือน Claude) */
    .msg-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
        opacity: 0.6;
    }
    .msg-label-ai   { color: #0d9488; }
    .msg-label-user { color: #94a3b8; text-align: right; }

    /* ==========================================
       Chat — Claude-style (Pure HTML render)
    ========================================== */

    /* ซ่อน avatar ของ Streamlit ทั้งหมด */
    [data-testid="stChatMessage"] {
        display: none !important;
    }

    /* wrapper หลักของ message แต่ละอัน */
    .chat-row {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        margin-bottom: 1.6rem;
        animation: fadeUp 0.25s ease;
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* AI — ชิดซ้าย */
    .chat-row.ai  { flex-direction: row; }
    /* User — ชิดขวา */
    .chat-row.user { flex-direction: row-reverse; }

    /* Avatar วงกลม */
    .chat-avatar {
        width: 36px; height: 36px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.95rem;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .chat-avatar.ai   { background: rgba(13,148,136,0.25); color: #2dd4bf; border: 1px solid rgba(13,148,136,0.4); }
    .chat-avatar.user { background: rgba(99,102,241,0.25); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.4); }

    /* Bubble content */
    .chat-bubble {
        max-width: 70%;
        line-height: 1.85;
        font-size: 1rem;
    }
    /* เอา text align ของ user ไปทางขวา */
    .chat-row.user .chat-bubble { text-align: left; }

    /* AI — ไม่มีกล่อง ข้อความสะอาด */
    .chat-bubble.ai-msg {
        color: #e2e8f0;
        padding: 0.2rem 0;
    }

    /* User — bubble สีเข้ม */
    .chat-bubble.user-msg {
        background: rgba(99,102,241,0.15);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 18px 4px 18px 18px;
        padding: 0.75rem 1.15rem;
        color: #f1f5f9;
    }

    /* Sender label */
    .chat-sender {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
        opacity: 0.55;
    }
    .chat-sender.ai   { color: #2dd4bf; }
    .chat-sender.user { color: #a5b4fc; }

    /* Code ใน bubble */
    .chat-bubble code {
        background: rgba(15,23,42,0.8);
        border: 1px solid #334155;
        border-radius: 5px;
        padding: 1px 6px;
        font-size: 0.87rem;
        color: #7dd3fc;
        font-family: 'Fira Code', monospace;
    }

    /* Chat input — clean minimal */
    [data-testid="stChatInput"] > div {
        border-radius: 14px !important;
        border: 1px solid #1e3a5f !important;
        background: rgba(15,23,42,0.7) !important;
        backdrop-filter: blur(10px);
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    [data-testid="stChatInput"] > div:focus-within {
        border-color: #0d9488 !important;
        box-shadow: 0 0 0 3px rgba(13,148,136,0.15) !important;
    }

    /* Legend ใน Graph Tab */
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        margin-right: 8px;
    }
    .legend-person  { background: rgba(13, 148, 136, 0.2); border: 1px solid #0d9488; color: #5eead4; }
    .legend-org     { background: rgba(14, 165, 233, 0.2); border: 1px solid #0ea5e9; color: #7dd3fc; }
    .legend-doc     { background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #a5b4fc; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ==========================================
# 2. ฟังก์ชัน Helper สำหรับ Render ไอคอน HTML
# ==========================================
def icon(fa_class: str, extra_class: str = "") -> str:
    """สร้าง HTML tag ของ Font Awesome icon"""
    return f'<i class="fa-solid {fa_class} {extra_class}"></i>'


# ==========================================
# 3. Session State & Callbacks
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed" not in st.session_state:
    st.session_state.indexed = False
if "workflow_app" not in st.session_state:
    st.session_state.workflow_app = None
# flag สำหรับควบคุม: กำลังประมวลผลอยู่หรือไม่
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
# flag สำหรับขอหยุด: ผู้ใช้กดปุ่ม Stop
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

def clear_chat_history():
    """ล้างประวัติการสนทนาทั้งหมด"""
    st.session_state.messages = []

def request_stop():
    """Callback สำหรับปุ่ม Stop — ตั้ง flag ขอหยุดประมวลผล"""
    st.session_state.stop_requested = True



# ==========================================
# 4. Mock-up Backend Functions
# ==========================================
def process_indexing_pipeline(files: List[Any]) -> bool:
    """
    ประมวลผล PDF จริงผ่าน DocumentProcessor → ChromaVectorStore → Neo4jGraphStore
    โดยล้างข้อมูลเก่าใน ChromaDB ออกก่อนทุกครั้ง เพื่อให้ตอบตาม PDF ใหม่เสมอ
    คืนค่า True เมื่อสำเร็จ, False เมื่อเกิดข้อผิดพลาดหรือถูก stop
    """
    # รีเซ็ต flag stop ก่อนเริ่ม และตั้ง flag ว่ากำลังประมวลผล
    st.session_state.stop_requested = False
    st.session_state.is_processing = True

    try:
        # import backend เฉพาะตอนกดปุ่ม เพื่อไม่ให้ช้าตอนเปิดแอป
        from src.utils.document_loader import DocumentProcessor
        from src.database.vector_store import ChromaVectorStore
        from src.database.graph_store import Neo4jGraphStore
        from src.agents.graph_workflow import create_workflow
    except ImportError as e:
        st.error(f"❌ โหลด Backend Module ไม่ได้: {e}\n\nกรุณาตรวจสอบว่าติดตั้ง dependencies ครบแล้ว")
        st.session_state.is_processing = False
        return False

    try:
        with st.status("กำลังเริ่มระบบ AI ประมวลผลเอกสาร...", expanded=True) as status:

            # --- ขั้นที่ 1: บันทึกไฟล์ที่อัปโหลดลงดิสก์ชั่วคราว ---
            st.write("📥 รับและบันทึกไฟล์ PDF ที่อัปโหลด...")
            processor = DocumentProcessor()
            all_chunks = []

            with tempfile.TemporaryDirectory() as tmp_dir:
                for uploaded_file in files:
                    # ตรวจสอบ flag ขอหยุดก่อนเริ่มประมวลผลแต่ละไฟล์
                    if st.session_state.stop_requested:
                        status.update(label="⏹️ หยุดการประมวลผลตามคำขอ", state="error", expanded=False)
                        st.warning("⏹️ หยุดประมวลผลแล้ว ยังไม่ได้สร้าง Index")
                        st.session_state.is_processing = False
                        return False

                    tmp_path = os.path.join(tmp_dir, uploaded_file.name)
                    with open(tmp_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    st.write(f"  ✂️ หั่นข้อความจาก: `{uploaded_file.name}`")
                    chunks = processor.process_document(tmp_path)
                    all_chunks.extend(chunks)
                    st.write(f"  ✅ ได้ {len(chunks)} Chunks")

            if not all_chunks:
                status.update(label="❌ ไม่พบข้อความในเอกสาร กรุณาตรวจสอบไฟล์", state="error")
                st.session_state.is_processing = False
                return False

            # ตรวจ stop อีกครั้งก่อนขั้น ChromaDB (ขั้นที่ใช้เวลานาน)
            if st.session_state.stop_requested:
                status.update(label="⏹️ หยุดการประมวลผลตามคำขอ", state="error", expanded=False)
                st.warning("⏹️ หยุดก่อนบันทึก ChromaDB")
                st.session_state.is_processing = False
                return False

            # --- ขั้นที่ 2: ล้างข้อมูลเก่าแล้วบันทึกลง ChromaDB ใหม่ ---
            st.write("🗑️ ล้างข้อมูลเก่าใน ChromaDB และบันทึก Embeddings ใหม่...")
            vector_store = ChromaVectorStore()
            # ลบ collection เก่าทิ้งทั้งหมด แล้วสร้างใหม่ด้วยข้อมูลปัจจุบัน
            vector_store.vector_store.delete_collection()
            # สร้าง instance ใหม่หลังลบ collection เพื่อรีเซ็ต connection
            vector_store = ChromaVectorStore()
            vector_store.add_documents(all_chunks)
            st.write(f"  ✅ บันทึก {len(all_chunks)} Chunks ลง ChromaDB เรียบร้อย")

            # ตรวจ stop อีกครั้งก่อนขั้น Neo4j
            if st.session_state.stop_requested:
                status.update(label="⏹️ หยุดการประมวลผลตามคำขอ", state="error", expanded=False)
                st.warning("⏹️ หยุดก่อนขั้น Neo4j (ChromaDB บันทึกเรียบร้อยแล้ว)")
                st.session_state.is_processing = False
                return False

            # --- ขั้นที่ 3: สกัด Knowledge Graph และบันทึกลง Neo4j ---
            st.write("🕸️ LLM กำลังสกัด Entity และความสัมพันธ์ → Neo4j...")
            try:
                graph_store = Neo4jGraphStore()
                # ล้างข้อมูลกราฟเก่าก่อนบันทึกใหม่
                with graph_store.driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
                graph_store.process_and_save(all_chunks)
                st.write("  ✅ วาด Knowledge Graph ลง Neo4j เรียบร้อย")
            except Exception as e:
                st.write(f"  ⚠️ Neo4j ไม่พร้อม (ข้าม): {e}")

            # --- ขั้นที่ 4: สร้าง LangGraph Workflow และ cache ไว้ใน Session ---
            st.write("🤖 สร้าง AI Agent Workflow...")
            st.session_state.workflow_app = create_workflow()
            # ตั้งสถานะ indexed เมื่อสำเร็จจริงเท่านั้น
            st.session_state.indexed = True
            st.session_state.is_processing = False

            status.update(
                label=f"✨ เรียนรู้เอกสารเรียบร้อย! ({len(all_chunks)} Chunks) พร้อมตอบคำถามแล้ว",
                state="complete",
                expanded=False
            )
            return True

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในขั้นตอนประมวลผล:\n\n`{type(e).__name__}: {e}`")
        st.session_state.is_processing = False
        return False


def get_ai_response(question: str) -> str:
    """
    เรียก LangGraph Multi-Agent Workflow จริง เพื่อตอบคำถามจากเอกสารที่ index ไว้
    """
    workflow_app = st.session_state.get("workflow_app")
    if workflow_app is None:
        return "⚠️ กรุณาอัปโหลดและประมวลผลเอกสารก่อนครับ"

    # สร้าง initial state ตามโครงสร้าง AgentState
    initial_state = {
        "question": question,
        "route_decision": "",
        "vector_context": [],
        "graph_context": [],
        "final_answer": "",
    }

    try:
        result = workflow_app.invoke(initial_state)
        return result.get("final_answer", "ขออภัย ไม่สามารถสร้างคำตอบได้")
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในระบบ Agent: {e}"


# ==========================================
# 5. Interactive Knowledge Graph
# ==========================================
def _node_color_by_label(label: str) -> str:
    """กำหนดสีให้ Node ตาม Label ประเภทใน Neo4j"""
    palette = {
        "PERSON":       "#0d9488",  # teal — บุคคล
        "ORGANIZATION": "#0ea5e9",  # blue — องค์กร/สถาบัน
        "LOCATION":     "#f59e0b",  # amber — สถานที่
        "ROLE":         "#a78bfa",  # purple — ตำแหน่ง
        "SKILL":        "#34d399",  # green — ทักษะ
        "DOCUMENT":     "#6366f1",  # indigo — เอกสาร
    }
    return palette.get(label.upper(), "#94a3b8")  # slate สำหรับ type ที่ไม่รู้จัก


def render_knowledge_graph() -> Any:
    """
    ดึงข้อมูล Node และ Edge จาก Neo4j จริง แล้ว render ด้วย streamlit-agraph
    หาก Neo4j ไม่พร้อมหรือยังไม่มีข้อมูล จะแสดงข้อความแจ้งแทน
    """
    # ยังไม่ได้ index เลย → แสดงข้อความแนะนำ
    if not st.session_state.get("indexed", False):
        st.info("กรุณาอัปโหลดและประมวลผลเอกสารก่อน เพื่อให้กราฟแสดงข้อมูลที่เกิดจากเอกสารของคุณ")
        return None

    try:
        import os
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
        )

        # ดึง Node และ Edge ทั้งหมดจาก Neo4j (จำกัดที่ 100 เพื่อ performance)
        query = """
        MATCH (s)-[r]->(t)
        RETURN
            s.id AS src_id, labels(s)[0] AS src_label,
            t.id AS tgt_id, labels(t)[0] AS tgt_label,
            type(r)   AS rel_type
        LIMIT 100
        """
        with driver.session() as session:
            records = list(session.run(query))
        driver.close()

        if not records:
            st.info("ยังไม่มีข้อมูลในกราฟ — Neo4j อาจยังไม่ได้รับข้อมูล หรือเอกสารไม่มี Entity ที่สกัดออกได้")
            return None

        # สร้าง Node โดยไม่ซ้ำกัน ใช้ id เป็น key
        node_map: dict = {}
        edges: list = []

        for row in records:
            src_id  = str(row["src_id"]) if row["src_id"] else "?"
            src_lbl = str(row["src_label"] or "UNKNOWN")
            tgt_id  = str(row["tgt_id"]) if row["tgt_id"] else "?"
            tgt_lbl = str(row["tgt_label"] or "UNKNOWN")
            rel     = str(row["rel_type"] or "RELATED")

            if src_id not in node_map:
                node_map[src_id] = Node(
                    id=src_id, label=src_id,
                    size=30, color=_node_color_by_label(src_lbl),
                    title=f"[{src_lbl}] {src_id}"
                )
            if tgt_id not in node_map:
                node_map[tgt_id] = Node(
                    id=tgt_id, label=tgt_id,
                    size=25, color=_node_color_by_label(tgt_lbl),
                    title=f"[{tgt_lbl}] {tgt_id}"
                )
            edges.append(Edge(source=src_id, target=tgt_id, label=rel))

        nodes = list(node_map.values())
        st.caption(f"แสดง {len(nodes)} โหนด และ {len(edges)} ความสัมพันธ์ (จาก Neo4j จริง)")
        config = Config(width="100%", height=560, directed=True, physics=True, hierarchical=False)
        return agraph(nodes=nodes, edges=edges, config=config)

    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถเชื่อมต่อ Neo4j ได้: `{e}`")
        return None


# ==========================================
# 6. Sidebar UI
# ==========================================
with st.sidebar:
    st.markdown(
        f'<div class="sidebar-title">{icon("fa-brain")} GraphRAG</div>',
        unsafe_allow_html=True
    )
    st.caption("Powered by LangGraph · Neo4j · ChromaDB")
    st.divider()

    # --- อัปโหลด ---
    st.markdown(
        f'<div class="section-header">{icon("fa-folder-open")} อัปโหลดเอกสาร</div>',
        unsafe_allow_html=True
    )
    pdfs = st.file_uploader(
        "ลากไฟล์ PDF มาวาง",
        type="pdf",
        accept_multiple_files=True,
        help="รองรับทั้ง PDF ข้อความและเอกสารสแกน (OCR)"
    )
    if pdfs:
        st.caption(f"เลือกแล้ว {len(pdfs)} ไฟล์")

    if st.button("เริ่มประมวลผลเอกสาร", use_container_width=True, key="btn_indexing", type="primary",
                   disabled=st.session_state.is_processing):
        if pdfs:
            # indexed จะถูก set ใน process_indexing_pipeline() เมื่อสำเร็จเท่านั้น
            process_indexing_pipeline(pdfs)
        else:
            st.warning("กรุณาเลือกไฟล์ PDF ก่อนกดปุ่ม")

    # แสดงปุ่ม Stop เฉพาะเมื่อกำลังประมวลผลอยู่
    if st.session_state.is_processing:
        st.button(
            "⏹️ หยุดการประมวลผล",
            use_container_width=True,
            key="btn_stop",
            on_click=request_stop,
            type="secondary",
        )

    st.divider()

    # --- สถานะระบบ ---
    st.markdown(
        f'<div class="section-header">{icon("fa-circle-nodes")} สถานะระบบ</div>',
        unsafe_allow_html=True
    )
    indexed = st.session_state.get("indexed", False)
    st.markdown(
        f'<div class="status-card {"status-ok" if indexed else "status-warn"}">'
        f'{icon("fa-circle-check") if indexed else icon("fa-circle-exclamation")}'
        f' {"เอกสารพร้อมค้นหา" if indexed else "ยังไม่มีเอกสารในระบบ"}'
        f'</div>',
        unsafe_allow_html=True
    )
    # TODO: เชื่อมต่อกับ ChromaDB และ Neo4j จริงเพื่อเช็ค Connection Status
    st.markdown(
        f'<div class="status-card status-warn">{icon("fa-database")} ChromaDB: Mock-up</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="status-card status-warn">{icon("fa-diagram-project")} Neo4j: Mock-up</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.button("ล้างประวัติการสนทนา", use_container_width=True, key="btn_clear", on_click=clear_chat_history)


# ==========================================
# 7. Main Content
# ==========================================
st.markdown(
    f'<div class="page-title">{icon("fa-robot")} GraphRAG Intelligent Assistant</div>',
    unsafe_allow_html=True
)
st.markdown("ระบบแชทอัจฉริยะพลัง **Knowledge Graph** + **Vector Search** ทำงานร่วมกันผ่าน Multi-Agent")
st.markdown("")

tab1, tab2 = st.tabs(["แชทกับ AI", "ดูกราฟความสัมพันธ์"])

# ---- TAB 1: CHAT ----
with tab1:
    # Welcome Screen สำหรับผู้ใช้ใหม่
    if not st.session_state.indexed and not st.session_state.messages:
        st.markdown(f"""
        <div class="welcome-card">
            <div class="big-icon">{icon("fa-robot")}</div>
            <h2>ยินดีต้อนรับสู่ GraphRAG Assistant</h2>
            <p>เริ่มต้นโดยอัปโหลดเอกสาร PDF ในแผงซ้ายมือ จากนั้นกดให้ AI เรียนรู้ แล้วพิมพ์คำถามได้ที่นี่เลยครับ</p>
            <div class="flow-steps">
                <div class="flow-step">
                    {icon("fa-file-arrow-up")}
                    <span>อัปโหลด PDF</span>
                </div>
                <div class="flow-arrow">{icon("fa-arrow-right")}</div>
                <div class="flow-step">
                    {icon("fa-gears")}
                    <span>ประมวลผล</span>
                </div>
                <div class="flow-arrow">{icon("fa-arrow-right")}</div>
                <div class="flow-step">
                    {icon("fa-comments")}
                    <span>ถามคำถาม</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # แสดงประวัติแชทด้วย Pure HTML (Claude-style)
    # ==========================================

    def render_bubble(role: str, content: str) -> str:
        """สร้าง HTML bubble 1 อัน — AI ซ้าย, User ขวา เหมือน Claude"""
        import html as _html
        import re
        safe = _html.escape(content)
        safe = safe.replace("\n", "<br>")
        safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
        safe = re.sub(r'`([^`]+)`', r'<code>\1</code>', safe)

        if role == "assistant":
            return f"""
            <div class="chat-row ai">
                <div class="chat-avatar ai"><i class="fa-solid fa-robot"></i></div>
                <div class="chat-bubble">
                    <div class="chat-sender ai">GraphRAG AI</div>
                    <div class="ai-msg">{safe}</div>
                </div>
            </div>"""
        else:
            return f"""
            <div class="chat-row user">
                <div class="chat-avatar user"><i class="fa-solid fa-user"></i></div>
                <div class="chat-bubble">
                    <div class="chat-sender user">คุณ</div>
                    <div class="user-msg">{safe}</div>
                </div>
            </div>"""

    # render ประวัติทั้งหมดในครั้งเดียว (ประสิทธิภาพดีกว่า loop ที่ render ทีละ bubble)
    if st.session_state.messages:
        all_html = "".join(
            render_bubble(m["role"], m["content"])
            for m in st.session_state.messages
        )
        st.markdown(all_html, unsafe_allow_html=True)

    # Chat Input + แสดง bubble ใหม่ทันที
    placeholder = (
        "พิมพ์คำถามเกี่ยวกับเอกสารของคุณ..."
        if st.session_state.indexed
        else "กรุณาอัปโหลดและประมวลผลเอกสารก่อน แล้วค่อยถามคำถามครับ"
    )
    if query := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": query})
        st.markdown(render_bubble("user", query), unsafe_allow_html=True)
        with st.spinner("กำลังค้นข้อมูล..."):
            ans = get_ai_response(query)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.markdown(render_bubble("assistant", ans), unsafe_allow_html=True)

# ---- TAB 2: KNOWLEDGE GRAPH ----
with tab2:
    st.markdown(
        f'<div class="page-title" style="font-size:1.4rem;">{icon("fa-diagram-project")} กราฟความสัมพันธ์ (Interactive)</div>',
        unsafe_allow_html=True
    )
    st.caption("ลากโหนดเพื่อจัดเรียง | เลื่อน Mouse Wheel เพื่อซูม | คลิกโหนดเพื่อดูรายละเอียด")

    # Legend
    st.markdown(f"""
    <div style="margin: 0.5rem 0 1rem;">
        <span class="legend-item legend-person">{icon("fa-user")} บุคคล/นิสิต</span>
        <span class="legend-item legend-org">{icon("fa-building-columns")} สถาบัน/องค์กร</span>
        <span class="legend-item legend-doc">{icon("fa-file-lines")} เอกสาร</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    with st.container(border=True):
        clicked = render_knowledge_graph()

    if clicked:
        st.success(f"เลือก Node: **{clicked}** — ใน Phase ต่อไปจะแสดง Metadata เพิ่มเติม")
    else:
        st.info("คลิกที่โหนดใดๆ เพื่อดูข้อมูลเพิ่มเติม")
