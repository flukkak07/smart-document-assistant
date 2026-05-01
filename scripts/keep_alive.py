import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# โหลดค่าจาก Environment (ถ้ามี)
load_dotenv()

def ping_neo4j():
    """
    ฟังก์ชันสำหรับส่ง Query ง่ายๆ ไปหา Neo4j เพื่อไม่ให้มันหลับ
    """
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not uri or not password:
        print("[Keep-Alive] ❌ Error: ไม่พบข้อมูลการเชื่อมต่อใน Environment Variables")
        return

    print(f"[Keep-Alive] 📡 กำลังส่งสัญญาณสะกิด Neo4j AuraDB ที่: {uri}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # รัน Query ที่เบาที่สุดเพื่อเช็คสถานะ
            result = session.run("RETURN 1 as ping")
            record = result.single()
            if record and record["ping"] == 1:
                print("[Keep-Alive] ✅ สำเร็จ! Neo4j ยังตื่นอยู่")
        driver.close()
    except Exception as e:
        print(f"[Keep-Alive] ❌ เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    ping_neo4j()
