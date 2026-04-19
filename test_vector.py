import os
from src.utils.document_loader import DocumentProcessor
from src.database.vector_store import ChromaVectorStore

def main():
    print("=" * 50)
    print("เริ่มทดสอบจำลองภาพรวม Phase 3: Retriever Pipeline")
    print("=" * 50)
    
    # 1. ปลุกระบบอ่านฝั่ง Document 
    loader = DocumentProcessor()
    data_folder = "data"
    
    # ให้ระบบ Loader ทำงานและดึง Chunks ทั้งหมดกลับมา
    chunks = loader.process_directory(data_folder)
    
    if not chunks:
        print("[Error] ไม่พบไฟล์ที่อ่านได้ กรุณาใส่ไฟล์ PDF ทดสอบลงในโฟลเดอร์ 'data' ก่อนนะครับ")
        return
        
    print("-" * 50)
        
    # 2. ปลุกระบบฐานข้อมูล (Vector Store) และโยนข้อมูลใส่เข้าสมอง
    vector_db = ChromaVectorStore()
    vector_db.add_documents(chunks)
    
    print("-" * 50)
    # 3. จำลองการค้นหาเสมือนเวลา User พิมพ์เข้าแชท
    print("ทดสอบระบบดึงข้อมูล (Retriever Test)")
    print("=" * 50)
    
    # ผู้ใช้สามารถลองพิมพ์หาอะไรก็ได้ที่อยู่ในเอกสาร เช่น 'มหาวิทยาลัย'
    query = input("กรุณาพิมพ์คำค้นหาที่คุณต้องการทดสอบ (เว้นว่างแล้วกด Enter เพื่อใช้ค่าเริ่มต้น): ")
    if not query.strip():
        query = "มหาวิทยาลัยเกษตรศาสตร์"

    # ตั้งค่าดึงก้อนข้อมูลกลับมาสัก 2 ก้อนเพื่อดูว่ามีความแม่นยำไหม
    results = vector_db.similarity_search(query, k=2)
    
    print(f"\n[สรุปผลลัพธ์ที่ตรงกับ '{query}' มากที่สุด]")
    if not results:
        print("ไม่พบเอกสารใดที่ตรงกับคำค้นหาเลย")
        
    for i, res in enumerate(results):
        source_file = os.path.basename(res.metadata.get('source', 'Unknown'))
        page_num = res.metadata.get('page', 'Unknown')
        
        print(f"\n>> อันดับ {i+1} [แหล่งที่มา: {source_file} หน้าที่: {page_num}]")
        # แสดงตัวอย่างข้อความสัก 200 ตัวอักษร
        print(f"'{res.page_content[:200]}...'")

if __name__ == "__main__":
    main()
