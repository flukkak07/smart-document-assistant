from langgraph.graph import StateGraph, START, END
from src.agents.state import AgentState
from src.agents.router_agent import RouterAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.synthesizer_agent import SynthesizerAgent

def create_workflow() -> StateGraph:
    """
    หัวใจหลักของการรวบรวม Agent ให้อยู่ภายใต้กรอบของ LangGraph
    เสมือนการวาดพิมพ์เขียว (Flowchart) ว่าเมื่อมีคนพิมพ์คำถาม ระบบจะเดินรถไปทางไหนบ้าง
    """
    # 1. เริ่มวาดกระดานด้วยเทมเพลต State ที่เราประดิษฐ์ไว้
    workflow = StateGraph(AgentState)
    
    # 2. ปลุกวิญญาณลูกน้องออกมาเตรียมพร้อม
    router = RouterAgent()
    retriever = RetrieverAgent()
    synthesizer = SynthesizerAgent()
    
    # 3. สร้าง Node (จุดจอดรถ หรือด่านกระบวนการทำงาน)
    workflow.add_node("router", router.route)
    workflow.add_node("vector_retriever", retriever.retrieve_vector)
    workflow.add_node("graph_retriever", retriever.retrieve_graph)
    workflow.add_node("synthesizer", synthesizer.synthesize)
    
    # 4. ฟังก์ชันสำหรับคุมประแจสับรางรถไฟ (Conditional Routing)
    def route_decision(state: AgentState):
        decision = state.get("route_decision", "both")
        if decision == "vector":
            return ["vector_retriever"]
        elif decision == "graph":
            return ["graph_retriever"]
        else:
            return ["vector_retriever", "graph_retriever"]

    # 5. ลากเส้นทางให้ระบบไหล (Edges)
    
    # ด่าน 1: เริ่มต้น (START) ต้องวิ่งไปหา Router (แจกงาน) ก่อนเสมอ
    workflow.add_edge(START, "router")
    
    # ด่าน 2: Router สร้างทางแยก (Conditional Edges)
    workflow.add_conditional_edges(
        "router",           # ปล่อยรถจากสถานี router
        route_decision,     # ให้ฟังก์ชัน route_decision เป็นคนดูป้ายสับราง
        {
            "vector_retriever": "vector_retriever",
            "graph_retriever": "graph_retriever"
        }
    )
    
    # ด่าน 3: เมื่อ Retriever หุ่นยนต์ไปดึงของมาเสร็จ ก็ต้องโยนมาให้ Synthesizer เป็นคนสรุปคำตอบ
    workflow.add_edge("vector_retriever", "synthesizer")
    workflow.add_edge("graph_retriever", "synthesizer")
    
    # ด่าน 4: Synthesizer ตอบเสร็จ ให้จบรอบการทำงานทันที (END)
    workflow.add_edge("synthesizer", END)
    
    # ห่อรวมทั้งหมดให้กลายเป็นฟังก์ชันพร้อมรัน (เหมือน Export โปรแกรม)
    app = workflow.compile()
    return app
