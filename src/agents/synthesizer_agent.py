from typing import Dict, Any, AsyncGenerator
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState

class SynthesizerAgent:
    """
    เอเจนท์ผู้รวบรวมเนื้อหา (Synthesizer) ทำหน้าที่นำข้อมูลจากทุกแหล่ง (Vector + Graph)
    มาสังเคราะห์และเรียบเรียงเป็นคำตอบที่สละสลวยและแม่นยำ
    
    Attributes:
        llm (ChatGroq): อินสแตนซ์ของ LLM สำหรับการสรุปเนื้อหา
        prompt (ChatPromptTemplate): แม่แบบข้อความสำหรับการสั่งการ AI
    """

    def __init__(self) -> None:
        """เริ่มต้นการตั้งค่า Synthesizer Agent"""
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.5)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือปัญญาประดิษฐ์ผู้ช่วยระดับมันสมอง (Synthesizer Agent)
หน้าที่ของคุณคือ ตอบคำถามของผู้ใช้ "โดยใช้ข้อมูลจาก Context ที่หามาให้เท่านั้น" ห้ามมโนหรือแต่งเรื่องขึ้นเอง
- หากข้อมูลมี Graph Context: ให้ใช้มันเพื่ออธิบายสถานะความสัมพันธ์ เช่น ใครอยู่ที่ไหน, ใครทำหน้าที่อะไร 
- หากข้อมูลมี Vector Context: ให้ใช้ประกอบเพื่อลงลึกรายละเอียดเนื้อหา 
- หากผู้ใช้ถามทักทาย ให้ทักทายตอบปกติด้วยความสุภาพ
- หากในแหล่งข้อมูลไม่มีคำตอบใดที่เกี่ยวข้องกันเลย ให้ตอบตรงๆว่า "ขออภัยครับ ไม่พบข้อมูลดังกล่าวในเอกสาร"

ตอบเป็นภาษาไทย ให้กระชับ สละสลวย และอ่านง่ายที่สุด"""),
            ("human", """คำถามจากผู้ใช้: {question}

แหล่งข้อมูลที่ค้นพบจากเอกสาร (Vector Context):
{vector_context}

แหล่งข้อมูลที่ค้นพบจากกราฟ (Graph Context):
{graph_context}

เรียบเรียงคำตอบของคุณ:""")
        ])
        self.chain = self.prompt | self.llm

    def _format_context(self, state: AgentState) -> Dict[str, str]:
        """จัดรูปแบบบริบทให้สวยงามก่อนส่งให้ LLM (Internal use)"""
        v_context = ""
        if state.get("vector_context"):
            for i, d in enumerate(state["vector_context"]):
                page = d.metadata.get('page', 'N/A')
                v_context += f"- [หน้า {page}]: {d.page_content}\n"
                
        g_context = ""
        if state.get("graph_context"):
            for i, g in enumerate(state["graph_context"]):
                g_context += f"- {g}\n"
                
        return {
            "vector_formatted": v_context or "ไม่มีข้อมูลเชิงลึกใน Vector",
            "graph_formatted": g_context or "ไม่มีข้อมูลความสัมพันธ์ใน Graph"
        }

    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        """
        สังเคราะห์คำตอบแบบปกติ (Blocking)
        """
        print("[Synthesizer Agent] ✍️ กำลังเรียบเรียงข้อมูลเพื่อตอบคำถาม...")
        contexts = self._format_context(state)
        
        response = self.chain.invoke({
            "question": state["question"],
            "vector_context": contexts["vector_formatted"],
            "graph_context": contexts["graph_formatted"]
        })
        
        print("[Synthesizer Agent] ✨ ร่างคำตอบเสร็จสิ้น!")
        return {"final_answer": response.content}

    async def synthesize_stream(self, state: AgentState) -> AsyncGenerator[str, None]:
        """
        สังเคราะห์คำตอบแบบ Stream (Non-blocking)
        """
        print("[Synthesizer Agent] 🌊 กำลังเริ่มสตรีมคำตอบ...")
        contexts = self._format_context(state)
        
        async for chunk in self.chain.astream({
            "question": state["question"],
            "vector_context": contexts["vector_formatted"],
            "graph_context": contexts["graph_formatted"]
        }):
            if chunk.content:
                yield chunk.content
