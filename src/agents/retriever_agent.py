from typing import Dict, Any, List
from src.agents.state import AgentState
from src.database.vector_store import Neo4jVectorStore
from src.database.graph_store import Neo4jGraphStore

class RetrieverAgent:
    """
    ลูกน้องแผนกค้นหาข้อมูล มีทักษะวิ่งไปหาตู้ Database ทั้งสองแบบ
    """
    def __init__(self) -> None:
        """
        โหลดอินสแตนซ์ของ ChromaDB และ Neo4j ทิ้งไว้เพื่อรอรับคำสั่งค้นหา
        """
        # โหลดการเชื่อมต่อ Database ทิ้งไว้ 
        self.vector_store = Neo4jVectorStore()
        self.graph_store = Neo4jGraphStore()

    def retrieve_vector(self, state: AgentState) -> Dict[str, Any]:
        """
        ดึงข้อมูลเชิงความหมายจาก Vector Database ด้วยวิธี Similarity Search
        
        Args:
            state (AgentState): ความจำปัจจุบันที่มีคำถามของผู้ใช้อยู่
            
        Returns:
            Dict[str, Any]: Dictionary เพื่ออัปเดตช่อง vector_context
        """
        print("[Vector Retriever] 📄 กำลังค้นหาข้อมูลเอกสารจาก Neo4j Vector...")
        results = self.vector_store.similarity_search(state["question"], k=3)
        print(f"[Vector Retriever] ✅ พบเอกสารที่ใกล้เคียงจำนวน {len(results)} ชิ้น")
        return {"vector_context": results}

    def retrieve_graph(self, state: AgentState) -> Dict[str, Any]:
        """
        ดึงข้อมูลความสัมพันธ์เชิงข่ายใยจาก Graph Database ด้วยภาษา Cypher
        
        Args:
            state (AgentState): ความจำปัจจุบันที่มีคำถามของผู้ใช้อยู่
            
        Returns:
            Dict[str, Any]: Dictionary เพื่ออัปเดตช่อง graph_context (แปลงโครงสร้างเส้นทางเป็น String list)
        """
        print("[Graph Retriever] 🕸️ กำลังค้นหาข้อมูลความสัมพันธ์จาก Neo4j...")
        
        # ตัวอย่าง Query เบื้องต้น: ดึงความสัมพันธ์ทั้งหมดที่อยู่ใกล้เคียงกัน (สมมติระบบดึงมาสุด 10 เส้นทาง)
        # *ในระบบใช้งานจริงขั้นแอดวานซ์ เราอาจจะส่งคำถามไปให้ LLM แปลงเป็น Cypher อีกที
        query = """
        MATCH (s)-[r]->(t) 
        RETURN labels(s)[0] AS type1, s.id AS entity1, type(r) AS relation, labels(t)[0] AS type2, t.id AS entity2
        LIMIT 10
        """
        
        with self.graph_store.driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            records = list(session.run(query))
        
        results = []
        for row in records:
            if row['entity1'] and row['entity2']:
                results.append(f"({row['entity1']}) --[{row['relation']}]--> ({row['entity2']})")
        
        print(f"[Graph Retriever] ✅ พบเส้นทางความสัมพันธ์รอบตัวจำนวน {len(results)} เส้นทาง")
        return {"graph_context": results}
