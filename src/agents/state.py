from typing import TypedDict, List, Optional
from langchain_core.documents import Document

class AgentState(TypedDict):
    """
    โครงสร้างกล่องความจำ (State) สำหรับระบบ Multi-Agent
    ใช้สำหรับเก็บข้อมูลและส่งต่อสถานะระหว่างเอเจนท์ต่างๆ ใน LangGraph
    
    Attributes:
        question (str): คำถามเริ่มต้นจากผู้ใช้
        route_decision (str): ผลการตัดสินใจเลือกเส้นทาง (vector, graph, หรือ both)
        vector_context (List[Document]): ข้อมูลที่ดึงได้จาก Vector Database
        graph_context (List[str]): ข้อมูลความสัมพันธ์ที่ดึงได้จาก Knowledge Graph
        final_answer (str): คำตอบที่สังเคราะห์เสร็จสมบูรณ์แล้ว
    """
    question: str
    route_decision: str
    vector_context: List[Document]
    graph_context: List[str]
    final_answer: str
