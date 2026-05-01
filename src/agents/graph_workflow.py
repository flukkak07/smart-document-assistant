from typing import List, Literal, Union
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from src.agents.state import AgentState
from src.agents.router_agent import RouterAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.synthesizer_agent import SynthesizerAgent

def create_workflow() -> CompiledStateGraph:
    """
    สร้างและตั้งค่าโครงสร้างการทำงาน (Workflow) ของ Multi-Agent System
    โดยใช้ LangGraph ในการควบคุมลำดับการทำงาน (Orchestration)
    
    Returns:
        CompiledStateGraph: กราฟสถานะที่พร้อมสำหรับการรันกระบวนการ RAG
    """
    # 1. กำหนดโครงสร้างกราฟโดยอ้างอิงจาก AgentState
    workflow = StateGraph(AgentState)
    
    # 2. เริ่มต้นอินสแตนซ์ของเอเจนท์ต่างๆ
    router = RouterAgent()
    retriever = RetrieverAgent()
    synthesizer = SynthesizerAgent()
    
    # 3. เพิ่มโหนด (Node) เข้าไปในกราฟ
    workflow.add_node("router", router.route)
    workflow.add_node("vector_retriever", retriever.retrieve_vector)
    workflow.add_node("graph_retriever", retriever.retrieve_graph)
    workflow.add_node("synthesizer", synthesizer.synthesize)
    
    # 4. นิยามฟังก์ชันสำหรับการตัดสินใจเลือกเส้นทาง (Conditional Routing)
    def route_decision(state: AgentState) -> List[str]:
        """
        ฟังก์ชันสับรางรถไฟตามผลการตัดสินใจของ Router Agent
        """
        decision = state.get("route_decision", "both")
        if decision == "vector":
            return ["vector_retriever"]
        elif decision == "graph":
            return ["graph_retriever"]
        return ["vector_retriever", "graph_retriever"]

    # 5. เชื่อมต่อเส้นทาง (Edges)
    
    # เริ่มต้นวิ่งไปหา Router เพื่อแจกจ่ายงาน
    workflow.add_edge(START, "router")
    
    # Router ส่งงานไปยังแผนกค้นหาตามเงื่อนไขที่วิเคราะห์ได้
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "vector_retriever": "vector_retriever",
            "graph_retriever": "graph_retriever"
        }
    )
    
    # หลังจากค้นหาเสร็จ (ไม่ว่าจะจากทางไหน) ให้ส่งไปสรุปที่ Synthesizer
    workflow.add_edge("vector_retriever", "synthesizer")
    workflow.add_edge("graph_retriever", "synthesizer")
    
    # เมื่อ Synthesizer ตอบคำตอบสุดท้ายเสร็จ ให้สิ้นสุดการทำงาน
    workflow.add_edge("synthesizer", END)
    
    # รวมและคอมไพล์เป็นโปรแกรมที่พร้อมทำงาน
    return workflow.compile()
