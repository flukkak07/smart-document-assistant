import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

def test_neo4j_cloud_connection() -> None:
    """
    ทดสอบการเชื่อมต่อ Neo4j AuraDB (Cloud), สร้าง Node และตรวจสอบผลลัพธ์
    """
    print("="*50)
    print("เริ่มการทดสอบ Neo4j AuraDB (Cloud)")
    print("="*50)
    
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not uri or not password:
         print("❌ ข้อผิดพลาด: ไม่พบ NEO4J_URI หรือ NEO4J_PASSWORD ในไฟล์ .env")
         return

    print(f"[Log] กำลังเชื่อมต่อที่: {uri}")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # 1. เคลียร์ข้อมูลเก่าเฉพาะโหนดทดสอบ (เพื่อไม่ให้กวนข้อมูลจริง)
            session.run("MATCH (n:TestNode) DETACH DELETE n")
            print("[Step 1] เคลียร์ข้อมูลทดสอบเดิมสำเร็จ")
            
            # 2. สร้าง Node ทดสอบ
            session.run("CREATE (n:TestNode {name: 'CloudTest', status: 'Active'})")
            print("[Step 2] สร้าง Node ทดสอบสำเร็จ")
            
            # 3. ดึงข้อมูลกลับมาดู
            result = session.run("MATCH (n:TestNode) RETURN n.name as name, n.status as status")
            record = result.single()
            if record:
                print(f"\n✅ ผลลัพธ์จาก Cloud: Name={record['name']}, Status={record['status']}")
                print("การเชื่อมต่อ Neo4j AuraDB สำเร็จสมบูรณ์!\n")
                
        driver.close()

    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการเชื่อมต่อ Neo4j: {e}")

if __name__ == "__main__":
    test_neo4j_cloud_connection()
