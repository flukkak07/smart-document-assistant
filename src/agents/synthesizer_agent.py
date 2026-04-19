from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState

class SynthesizerAgent:
    """
    Agent ผู้พิทักษ์ด่านสุดท้าย: หน้าที่คือนำซากข้อมูลดิบๆ (Vector + Graph) ทั้งหมด
    มารวมกับคำถามของผู้ใช้ และแต่งประโยคอธิบายใหม่ให้เป็นภาษาคน สละสลวย
    """
    def __init__(self) -> None:
        """
        เตรียมพร้อมเชื่อมต่อ LLM เพื่อใช้ปะติดปะต่อเนื้อหาเป็นภาษาเขียนธรรมชาติ
        โดยอิงตามบริบทเท่านั้น
        """
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

    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        """
        สกัดข้อความสุดท้าย คัดเลือกเนื้อหาที่มีประโยชน์มากที่สุดตอบเป็นข้อความเสร็จสมบูรณ์
        
        Args:
            state (AgentState): ความจำปัจจุบันที่เก็บ vector_context และ graph_context มาแล้ว
            
        Returns:
            Dict[str, Any]: Dictionary เพื่ออัปเดตช่อง final_answer
        """
        print("[Synthesizer Agent] ✍️ กำลังเรียบเรียงข้อมูลเพื่อตอบคำถาม...")
        
        # จัด Format ให้สวยๆ ก่อนส่งให้ LLM อ่าน
        v_context = ""
        if state.get("vector_context"):
            for i, d in enumerate(state["vector_context"]):
                v_context += f"- เอกสารอ้างอิง {i+1}: {d.page_content}\n"
                
        g_context = ""
        if state.get("graph_context"):
            for i, g in enumerate(state["graph_context"]):
                g_context += f"- กราฟความสัมพันธ์ {i+1}: {g}\n"
                
        response = self.chain.invoke({
            "question": state["question"],
            "vector_context": v_context or "ไม่มีข้อมูลเชิงลึกใน Vector",
            "graph_context": g_context or "ไม่มีข้อมูลความสัมพันธ์ใน Graph"
        })
        
        print("[Synthesizer Agent] ✨ ร่างคำตอบเสร็จสิ้น!")
        return {"final_answer": response.content}

    async def synthesize_stream(self, state: AgentState):
        """
        โหมดสตรีมมิ่ง: ส่งข้อความออกมาทีละชิ้น (Token) เพื่อให้หน้าจอแสดงผลได้รวดเร็วขึ้น
        """
        print("[Synthesizer Agent] 🌊 กำลังเริ่มสตรีมคำตอบ...")
        
        v_context = ""
        if state.get("vector_context"):
            for i, d in enumerate(state["vector_context"]):
                v_context += f"- อ้างอิงจากเอกสารหน้า {d.metadata.get('page', 'N/A')}: {d.page_content}\n"
                
        g_context = ""
        if state.get("graph_context"):
            for i, g in enumerate(state["graph_context"]):
                # g is a dict from graph_store
                g_context += f"- อ้างอิงจากความสัมพันธ์: {g}\n"
        
        # ใช้ .astream เพื่อดึงข้อมูลแบบ Async Generator
        async for chunk in self.chain.astream({
            "question": state["question"],
            "vector_context": v_context or "ไม่มีข้อมูลเชิงลึกใน Vector",
            "graph_context": g_context or "ไม่มีข้อมูลความสัมพันธ์ใน Graph"
        }):
            if chunk.content:
                yield chunk.content
