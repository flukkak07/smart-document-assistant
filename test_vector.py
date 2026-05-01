import os
from dotenv import load_dotenv
from src.database.vector_store import Neo4jVectorStore
from langchain_core.documents import Document

# โหลดค่าจากไฟล์ .env
load_dotenv()

def test_vector_connection():
    """
    ทดสอบการเชื่อมต่อ Neo4j Vector และ HuggingFace API
    """
    print("="*50)
    print("เริ่มการทดสอบ Neo4j Vector (Cloud)")
    print("="*50)
    
    try:
        # 1. เริ่มต้นคลาส
        vector_db = Neo4jVectorStore()
        print("[Step 1] เริ่มต้น Neo4jVectorStore สำเร็จ")
        
        # 2. ทดสอบค้นหา (แม้จะยังไม่มีข้อมูล)
        print("[Step 2] ทดสอบ Similarity Search (อาจจะไม่พบข้อมูลถ้ายังไม่ได้ Index)")
        results = vector_db.similarity_search("ทดสอบการเชื่อมต่อ", k=1)
        print(f"ผลการค้นหา: พบ {len(results)} รายการ")
        
        print("\n✅ การเชื่อมต่อ Vector Store เบื้องต้นสำเร็จ!")
        
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {str(e)}")
        print("\nกรุณาตรวจสอบ:")
        print("1. NEO4J_URI, USERNAME, PASSWORD ใน .env ถูกต้องหรือไม่")
        print("2. HUGGINGFACE_API_TOKEN ใน .env ถูกต้องและมีสิทธิ์ใช้งานหรือไม่")
        print("3. อินเทอร์เน็ตสามารถเชื่อมต่อ Neo4j AuraDB ได้หรือไม่")

if __name__ == "__main__":
    test_vector_connection()
