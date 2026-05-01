import os
from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState

load_dotenv()

class RouteDecision(BaseModel):
    """นิยามผลลัพธ์การตัดสินใจเลือกเส้นทาง"""
    decision: Literal["vector", "graph", "both"] = Field(
        description="เส้นทางค้นหา: 'vector' (เนื้อหา), 'graph' (ความสัมพันธ์), 'both' (ทั้งคู่)"
    )

class RouterAgent:
    """
    เอเจนท์ผู้วางแผนเส้นทาง (Router) ทำหน้าที่วิเคราะห์คำถาม
    เพื่อตัดสินใจว่าจะดึงข้อมูลจาก Vector Database หรือ Knowledge Graph
    
    Attributes:
        llm (ChatGroq): อินสแตนซ์ของ LLM สำหรับการตัดสินใจ
        router (Callable): ฟังก์ชันสกัดโครงสร้างการตัดสินใจ
    """

    def __init__(self) -> None:
        """เริ่มต้นการตั้งค่า Router Agent"""
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        self.router = self.llm.with_structured_output(RouteDecision)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือ AI อัจฉริยะผู้ช่วยแจกจ่ายงานประจำระบบ Agentic RAG
หน้าที่ของคุณคือ วิเคราะห์คำถามของผู้ใช้ และติดสินใจว่าจะดึงข้อมูลจากแหล่งใด:
- 'vector': ถ้าคำถามเกี่ยวกับรายละเอียดเนื้อหา, ข้อตกลง, ประโยคยาวๆ, คำนิยาม
- 'graph': ถ้าคำถามเกี่ยวกับความสัมพันธ์ เช่น ใครทำอะไร, เรียนที่ไหน, มีหน้าที่อะไร, เกี่ยวข้องกับใคร
- 'both': ถ้าคำถามซับซ้อนและรวมทั้งสองอย่าง
ถ้าไม่แน่ใจให้เลือก 'both' เสมอ เพื่อความปลอดภัยของข้อมูล"""),
            ("human", "คำถามที่ต้องการวิเคราะห์: {question}")
        ])
        self.chain = self.prompt | self.router

    def route(self, state: AgentState) -> Dict[str, Any]:
        """
        วิเคราะห์คำถามจาก State และระบุเส้นทางที่เหมาะสม
        
        Args:
            state (AgentState): สถานะปัจจุบันของกระบวนการทำงาน
            
        Returns:
            Dict[str, Any]: ผลลัพธ์การตัดสินใจเพื่ออัปเดตลงใน State
        """
        print("\n[Router Agent] 🧠 กำลังวิเคราะห์เจตนาของคำถาม...")
        try:
            result = self.chain.invoke({"question": state["question"]})
            path = result.decision if result else "both"
        except Exception as e:
            print(f"[Router Agent] Error: {str(e)} - สลับไปใช้โหมด 'both' เพื่อความปลอดภัย")
            path = "both"
            
        print(f"[Router Agent] 🚦 เส้นทางที่เลือก: {path.upper()}")
        return {"route_decision": path}
