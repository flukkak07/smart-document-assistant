import os
import chromadb
from neo4j import GraphDatabase
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

def test_chromadb_connection() -> None:
    """
    ทดสอบการเชื่อมต่อ สร้าง Collection, บันทึกข้อมูล และดึงข้อมูลใน ChromaDB (Vector Database)
    """
    print("กำลังทดสอบ ChromaDB...")
    try:
        # กำหนด Path เป็นโฟลเดอร์ data/chroma (จะเป็น Persistent DB บันทึกลง Disk)
        db_path = os.path.join("data", "chroma")
        client = chromadb.PersistentClient(path=db_path)
        
        collection_name = "test_collection"
        
        # ค้นหาและลบ Collection เก่าออก (เคลียร์ข้อมูลก่อนทดสอบ)
        try:
            client.delete_collection(name=collection_name)
            print(f"[Log] เคลียร์ข้อมูล Collection '{collection_name}' เดิมเรียบร้อยแล้ว")
        except Exception:
            # ไม่เป็นไร ถ้าหาไม่เจอแสดงว่ายังไม่เคยถูกสร้าง
            pass

        # สร้าง Collection ใหม่
        collection = client.create_collection(name=collection_name)
        print(f"[Log] สร้าง Collection '{collection_name}' สำเร็จ")
        
        # ทดสอบใส่ข้อมูล (พร้อม Embedding หยาบๆ หากไม่ใส่โมเดลให้ มันจะใช้ default)
        collection.add(
            documents=["สุนัขเป็นสัตว์เลี้ยงที่น่ารัก", "แมวชอบทำตัวหยิ่งๆ แต่ก็น่ารัก", "นกแก้วพูดได้"],
            metadatas=[{"topic": "dog"}, {"topic": "cat"}, {"topic": "bird"}],
            ids=["id1", "id2", "id3"]
        )
        print("[Log] เพิ่มข้อมูลทดสอบเข้า ChromaDB สำเร็จ")
        
        # ทดสอบดึงข้อมูล (Query)
        results = collection.query(
            query_texts=["สัตว์ชนิดไหนหยิ่ง?"],
            n_results=1
        )
        print(f"\nผลการค้นหาจาก ChromaDB: {results['documents']}")
        print("การทดสอบ ChromaDB เสร็จสมบูรณ์!\n")

    except Exception as e:
        print(f"ข้อผิดพลาด ChromaDB: {e}")


def test_neo4j_connection() -> None:
    """
    ทดสอบการเชื่อมต่อ Neo4j (Knowledge Graph), สร้าง Node, Relationship และเคลียร์ข้อมูล
    """
    print("กำลังทดสอบ Neo4j...")
    
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not password or password == "your_neo4j_password_here":
         print("ข้อผิดพลาด: ไม่พบ NEO4J_PASSWORD ในไฟล์ .env หรือยังไม่ได้เปลี่ยนค่าเริ่มต้น")
         print("กรุณาติดตั้ง Neo4j Desktop และตั้งรหัสผ่าน ก่อนทดสอบฟังก์ชันนี้อีกครั้ง\n")
         return

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # ฟังก์ชันย่อยสำหรับเคลียร์ Graph ข้อมูลเก่า
        def clear_graph(tx) -> None:
            tx.run("MATCH (n) DETACH DELETE n")
            
        def create_test_graph(tx) -> None:
            tx.run(
                "CREATE (p:Person {name: 'สมชาย'}) "
                "CREATE (t:Technology {name: 'GraphRAG'}) "
                "CREATE (p)-[:LEARNS]->(t)"
            )
            
        def query_graph(tx):
            result = tx.run("MATCH (p:Person)-[r:LEARNS]->(t:Technology) RETURN p.name, type(r), t.name")
            return result.single()

        # นำกระบวนการไปรันผ่าน Session
        with driver.session() as session:
            # 1. ล้างข้อมูลเก่า
            session.execute_write(clear_graph)
            print("[Log] เคลียร์ข้อมูล Graph เดิมเรียบร้อยแล้ว")
            
            # 2. สร้าง Graph ทดสอบ
            session.execute_write(create_test_graph)
            print("[Log] สร้าง Node และ Relationship ทดสอบสำเร็จ")
            
            # 3. ดึงข้อมูลทดสอบมาดู
            record = session.execute_read(query_graph)
            if record:
                print(f"\nผลลัพธ์จาก Neo4j: {record['p.name']} {record['type(r)']} {record['t.name']}")
                
        driver.close()
        print("การทดสอบ Neo4j เสร็จสมบูรณ์!\n")

    except Exception as e:
        print(f"ข้อผิดพลาดในการเชื่อมต่อ Neo4j: {e}")

if __name__ == "__main__":
    print("=" * 40)
    print("เริ่มการทดสอบฐานข้อมูล (ChromaDB & Neo4j)")
    print("=" * 40)
    test_chromadb_connection()
    test_neo4j_connection()
    print("จบการทดสอบฐานข้อมูลทั้งหมด")
