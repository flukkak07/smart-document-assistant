from src.agents.graph_workflow import create_workflow

def main():
    print("=" * 60)
    print("🤖 ยินดีต้อนรับสู่ระบบ Smart Agentic GraphRAG")
    print("=" * 60)
    
    # 1. เสกและเปิดเครื่องระบบ LangGraph ที่เราเชื่อมเอาไว้
    app = create_workflow()
    
    print("\n[ระบบพร้อมใช้งานแล้ว พิมพ์คำถามของคุณลงมาได้เลย!]")
    
    # 2. ปล่อยลูปรอรับแชทจากผู้ใช้ตามปกติ
    while True:
        question = input("\nผู้ใช้ (พิมพ์ 'exit' เพื่อออก): ")
        
        if question.lower().strip() == 'exit':
            print("ลาก่อนครับ!")
            break
            
        if not question.strip():
            continue
            
        print("-" * 60)
        
        # 3. สานชิ้นส่วนคำถามลงใน State เริ่มต้น
        initial_state = {
            "question": question,
            "route_decision": "",
            "vector_context": [],
            "graph_context": [],
            "final_answer": ""
        }
        
        # 4. เดินเครื่อง! ส่งให้ LangGraph ดูแลส่วนที่เหลือทั้งหมด
        result = app.invoke(initial_state)
        
        # 5. รับคำตอบที่สรุปแล้วโชว์ให้ User เห็น
        print("\n\n🏆 [คำตอบจาก Agent]:")
        print(result["final_answer"])
        print("-" * 60)

if __name__ == "__main__":
    main()
