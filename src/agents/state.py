from typing import TypedDict, List
from langchain_core.documents import Document

class AgentState(TypedDict):
    """
    โครงสร้างกล่องความจำ (State) ที่ Agent ทุกตัวใน LangGraph จะเห็นและส่งต่อกันไปมา
    """
    question: str                   # คำถามจากผู้ใช้
    route_decision: str             # การตัดสินใจของ Router Agent ว่าจะไปทางไหน
    vector_context: List[Document]  # เนื้อหาที่ได้กลับมาจาก Vector Database
    graph_context: List[str]        # เส้นทางความสัมพันธ์ที่ได้จาก Neo4j
    final_answer: str               # คำตอบสุดท้ายที่จะพ่นให้ผู้ใช้ฟัง
