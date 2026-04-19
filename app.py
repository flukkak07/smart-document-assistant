import streamlit as st
import os

from src.utils.document_loader import DocumentProcessor
from src.database.vector_store import ChromaVectorStore
from src.database.graph_store import Neo4jGraphStore
from src.agents.graph_workflow import create_workflow

# เซ็ตค่าเริ่มต้นให้หน้าเว็บ
st.set_page_config(page_title="Agentic GraphRAG", page_icon="🤖", layout="wide")

# ==========================================
# 0. เตรียมความพร้อมของระบบหลังบ้าน (Cache ไว้จะได้ไม่โหลดซ้ำ)
# ==========================================
@st.cache_resource
def load_graph_agent():
    return create_workflow()

workflow_app = load_graph_agent()

# ==========================================
# 1. จัดฉาก Sidebar สำหรับหน้าต่างอัปโหลด
# ==========================================
with st.sidebar:
    st.title("📁 Document Processor")
    st.markdown("อัปโหลดเอกสาร PDF ลงในระบบเพื่อให้ทีมหมอผี AI ของเราช่วยศึกษาโครงสร้างและความสัมพันธ์แบบลึกซึ้ง")
    
    uploaded_files = st.file_uploader("ลากไฟล์ PDF มาวางที่นี่", type="pdf", accept_multiple_files=True)
    
    # ปุ่มรันระบบ
    if st.button("🚀 เริ่มฝังข้อมูลและสอน AI (Indexing)", use_container_width=True):
        if not uploaded_files:
            st.error("กรุณาอัปโหลดเอกสารก่อนครับ")
        else:
            with st.spinner("ระบบกำลังหั่นข้อมูลให้เป็นชิ้นๆ (Document Chunking)..."):
                # เซฟไฟล์ชั่วคราวลงใน /data
                os.makedirs("data", exist_ok=True)
                for f in uploaded_files:
                    path = os.path.join("data", f.name)
                    with open(path, "wb") as file:
                        file.write(f.getbuffer())
                
                # โหลดข้อมูล
                loader = DocumentProcessor()
                chunks = loader.process_directory("data")
                st.info(f"✨ หั่นเนื้อหาสำเร็จ ได้แฟ้มข้อมูลทั้งหมด {len(chunks)} Chunks")
                
            with st.spinner("กำลังแปลงเป็น Vector และบันทึกลงตาข่ายมิติ (ChromaDB)..."):
                vector_db = ChromaVectorStore()
                vector_db.add_documents(chunks)
                st.success("✅ บันทึกระยะทางเวกเตอร์ใส่ความทรงจำเรียบร้อย")
                
            with st.spinner("กำลังสกัดหาความสัมพันธ์ Entity และวาดลงกระดาน (Neo4j)..."):
                graph_db = Neo4jGraphStore()
                # ระบุจำนวนชิ้นจำกัด (3 ก้อน) เพื่อป้องกันปัญหา Rate Limit กับการใช้ API โควต้าฟรี
                graph_db.process_and_save(chunks[:3]) 
                st.success("🕸️ สร้างและผูกเส้น Knowledge Graph สำเร็จ!")

            st.balloons()
            
    st.divider()
    st.markdown("💡 **Tip:** อัปโหลดเสร็จแล้ว หันไปแชทและสนทนากับ AI เรื่องข้อมูลเหล่านี้ต่อได้ที่หน้าต่างขวามือเลย")

# ==========================================
# 2. จัดฉากหลัก สำหรับช่องแชทแบบ Real-time
# ==========================================
st.title("🤖 Smart Agentic GraphRAG")
st.caption("ระบบแชทผู้ช่วยอัจฉริยะ ที่มีตัวตน Agent แฝงอยู่เบื้องหลังคอยถกเถียงและทำงานร่วมกันเพื่อหาคำตอบที่สุดยอดที่สุด")

# เก็บบันทึกการคุยของ User ปัจจุบัน
if "messages" not in st.session_state:
    st.session_state.messages = []

# แสดงแชทเรื่อยๆ 
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# รอรับข้อความ
user_query = st.chat_input("พิมพ์คำถามของคุณที่นี่ (เช่น มหาวิทยาลัยเกษตรศาสตร์ มีข้อปฏิบัติอย่างไรบ้าง?)")

if user_query:
    # 1. เขียนคำถามฝั่งผู้ใช้
    with st.chat_message("user"):
        st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        
    # 2. ให้สมองกล Agent รัวความคิด
    with st.chat_message("assistant"):
        with st.spinner("🧠 ทีมคอมมานโด Agent กำลังประชุมวิเคราะห์เนื้อหาและกราฟ..."):
            initial_state = {
                "question": user_query,
                "route_decision": "",
                "vector_context": [],
                "graph_context": [],
                "final_answer": ""
            }
            
            # เตะข้อมูลเข้า Workflow 
            result = workflow_app.invoke(initial_state)
            
            # โชว์คำตอบลอยลม
            st.markdown(result["final_answer"])
            st.session_state.messages.append({"role": "assistant", "content": result["final_answer"]})
            
            # (ออปชันพิเศษโชว์พอร์ต) กล่องเปิดดูความคืบหน้าเบื้องหลังที่ Agent ไปคุ้ยมา
            with st.expander("🛠️ จิ้มเพื่อแอบดูว่าทีม Agent ใช้สมองซีกไหนหาคำตอบ!?"):
                st.write(f"**เส้นทางหลักที่หัวหน้า Router โยกไป:** `{result.get('route_decision', 'N/A').upper()}`")
                
                if result.get('vector_context'):
                    st.write(f"📄 แผนก Vector ดึงข้อความมาได้จำนวน: {len(result['vector_context'])} ชิ้น")
                
                if result.get('graph_context'):
                    st.write(f"🕸️ แผนก Graph ค้นตารางได้ความเชื่อมโยง: {len(result['graph_context'])} เส้นทาง")

