import os
from typing import Literal, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState

load_dotenv()

class RouteDecision(BaseModel):
    decision: Literal["vector", "graph", "both"] = Field(
        description="การตัดสินใจเลือกเส้นทางค้นหา ('vector' สำหรับข้อมูลเนื้อหา/ความหมาย, 'graph' สำหรับความสัมพันธ์/ใครทำอะไร, 'both' ถ้าต้องใช้ร่วมกัน)"
    )

class RouterAgent:
    """
    Agent ผู้ทำหน้าที่เป็นหัวหน้าแผนก คอยตัดสนใจว่าคำถามนี้ควรมอบหมายให้ 
    Vector Database (หาข้อมูลลึก) หรือ Graph Database (หาความสัมพันธ์) เป็นคนทำ
    """
    def __init__(self) -> None:
        """
        เตรียมความพร้อมเชื่อมต่อ Groq API LLM สำหรับตัดสินใจเลือกเส้นทาง
        """
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        # บังคับคำตอบออกให้เป็น JSON Pydantic เท่านั้น
        self.router = self.llm.with_structured_output(RouteDecision)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือ AI อัจฉริยะผู้ช่วยแจกจ่ายงานประจำระบบ Agentic RAG
หน้าที่ของคุณคือ วิเคราะห์คำถามของผู้ใช้ และติดสินใจว่าจะดึงข้อมูลจากแหล่งใด:
- 'vector': ถ้าคำถามเกี่ยวกับรายละเอียดเนื้อหา, ข้อตกลง, ประโยคยาวๆ, คำนิยาม
- 'graph': ถ้าคำถามเกี่ยวกับความสัมพันธ์ เช่น ใครทำอะไร, เรียนที่ไหน, มีหน้าที่อะไร, เกี่ยวข้องกับใคร
- 'both': ถ้าคำถามซับซ้อนและรวมทั้งสองอย่าง
ถ้าไม่แน่ใจให้เลือก 'both' เสมอ เพื่อความปลอดภัยของข้อมูล"""),
            ("human", "คำถาม: {question}")
        ])
        self.chain = self.prompt | self.router

    def route(self, state: AgentState) -> Dict[str, Any]:
        """
        อ่านคำถามจาก State ปัจจุบันและตัดสินผลลัพธ์ผ่าน LLM 
        
        Args:
            state (AgentState): ตัวแปรกล่องความจำที่เก็บโครงสร้างข้อมูลทั้งหมดเอาไว้
            
        Returns:
            Dict[str, Any]: คืนค่าออฟเจกต์เป็นส่วนย่อย (dict) เพื่อให้อัปเดต State ตรง field 'route_decision'
        """
        print("\n[Router Agent] 🧠 กำลังวิเคราะห์เจตนาของคำถาม...")
        try:
            decision = self.chain.invoke({"question": state["question"]})
            path = decision.decision
        except Exception:
            # Fallback หาก LLM รุ่นเล็กรวน ให้เลือก both ป้องกันข้อมูลหาย
            path = "both"
            
        print(f"[Router Agent] 🚦 ตัดสินใจส่งคำถามไปที่เส้นทาง: {path.upper()}")
        return {"route_decision": path}
