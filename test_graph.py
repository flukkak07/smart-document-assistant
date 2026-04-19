import sys
from src.utils.document_loader import DocumentProcessor
from src.database.graph_store import Neo4jGraphStore

def main():
    print("=" * 60)
    print("เริ่มทดสอบ Phase 4: Knowledge Graph Construction")
    print("=" * 60)
    
    # 1. โหลดเอกสาร
    loader = DocumentProcessor()
    chunks = loader.process_directory("data")
    if not chunks:
        print("[Error] ไม่พบไฟล์ที่อ่านได้ กรุณาตรวจสอบโฟลเดอร์ data/")
        sys.exit(1)
        
    print("-" * 60)
        
    # 2. ปลุกระบบฐานข้อมูล Graph (Neo4j Store) 
    graph_db = Neo4jGraphStore()
    
    # [เซฟตี้] จะเลือกเทสต์การส่งข้อมูลให้ LLM แค่ 2 Chunk แรก 
    # เพื่อประหยัดโควต้า Rate Limit ของ API ระหว่างเทสต์ หากรันฉบับเต็มค่อยเอา [:2] ออก
    test_chunks = chunks[:2]
    
    # สั่งประมวลผลวาด Node & Edge
    graph_db.process_and_save(test_chunks)
    
    print("-" * 60)
    print("ทดสอบดึงข้อมูลกราฟความสัมพันธ์ (Cypher Query Test)")
    print("=" * 60)
    
    # 3. ลองยิง Query ไปขอดึงลิสต์สิ่งที่ AI สร้างไว้มาโชว์ 
    query = """
    MATCH (s)-[r]->(t)
    RETURN labels(s)[0] AS SourceType, s.id AS Source, 
           type(r) AS Relationship, 
           labels(t)[0] AS TargetType, t.id AS Target
    LIMIT 5
    """
    
    with graph_db.driver.session() as session:
        result = session.run(query)
        records = list(result)
        
        if not records:
            print("ไม่พบความสัมพันธ์ในฐานข้อมูล")
        else:
            for i, row in enumerate(records):
                print(f"[{i+1}] ({row['SourceType']}) {row['Source']} --[{row['Relationship']}]--> ({row['TargetType']}) {row['Target']}")

if __name__ == "__main__":
    main()
