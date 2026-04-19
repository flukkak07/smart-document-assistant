import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

# โหลดค่าจากไฟล์ .env
load_dotenv()

def test_llm_connection() -> None:
    """
    ฟังก์ชันสำหรับทดสอบการเชื่อมต่อกับ LLM (ในกรณีนี้คือ Groq)
    จะทำการอ่าน GROQ_API_KEY จาก .env และลองส่งข้อความง่ายๆ ไปหาโมเดล
    """
    print("กำลังทดสอบการเชื่อมต่อ LLM (Groq)...")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("ข้อผิดพลาด: ไม่พบ GROQ_API_KEY ในไฟล์ .env หรือยังไม่ได้เปลี่ยนค่าเริ่มต้น")
        return
        
    try:
        # ใช้โมเดล llama-3.1-8b-instant ซึ่งเป็นรุ่นใหม่ที่เปิดให้ใช้ฟรีบน Groq
        llm = ChatGroq(model_name="llama-3.1-8b-instant")
        response = llm.invoke("สวัสดี ช่วยแนะนำตัวสั้นๆ ไม่เกิน 1 ประโยค")
        
        print("\n=== ผลลัพธ์จาก LLM ===")
        print(response.content)
        print("การเชื่อมต่อ LLM สำเร็จ!\n")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ LLM: {str(e)}")

def test_embedding_connection() -> None:
    """
    ฟังก์ชันสำหรับทดสอบการดาวน์โหลดและใช้งาน Embedding Model แบบ Local
    ใช้ไลบรารี HuggingFaceEmbeddings กับโมเดล all-MiniLM-L6-v2
    """
    print("กำลังเตรียมพร้อมและทดสอบ Embedding Model (HuggingFace)...")
    
    try:
        # กำหนดโมเดล Sentence Transformers ยอดนิยมที่มีขนาดเล็กและเบา
        model_name = "all-MiniLM-L6-v2"
        # ครั้งแรกที่รัน โค้ดนี้จะดาวน์โหลดโมเดลมาเก็บไว้ในเครื่อง
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        
        text_to_embed = "การทำ RAG เป็นเรื่องสนุก"
        vector = embeddings.embed_query(text_to_embed)
        
        print("\n=== ผลลัพธ์จาก Embedding Model ===")
        print(f"ข้อความที่ฝัง: '{text_to_embed}'")
        print(f"ขนาดของเวกเตอร์ (Dimensions): {len(vector)}")
        print(f"ตัวอย่างเวกเตอร์ 5 ค่าแรก: {vector[:5]}")
        print("การโหลด Embedding Model สำเร็จ!\n")
    except Exception as e:
         print(f"เกิดข้อผิดพลาดในการโหลด Embedding Model: {str(e)}")

if __name__ == "__main__":
    print("=" * 40)
    print("เริ่มการทดสอบโมเดล (LLM & Embeddings)")
    print("=" * 40)
    test_llm_connection()
    test_embedding_connection()
    print("จบการทดสอบโมเดลทั้งหมด")
