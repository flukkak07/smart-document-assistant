import os
from typing import List
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

class ChromaVectorStore:
    """
    คลาสสำหรับจัดการ Vector Database ด้วย Chroma
    แปลงข้อมูล Text chunks ให้กลายเป็นฐานข้อมูลตัวเลข (Embedding)
    และสามารถค้นหาเอกสารที่มีความหมายอ้างอิงตรงกับคำถามมากที่สุด 
    """
    def __init__(self, persist_directory: str = "chroma_db", collection_name: str = "smart_doc_assistant"):
        """
        เตรียมเชื่อมต่อโฟลเดอร์สำหรับเก็บไฟล์ ChromaDB และโหลดโมเดล Embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # ใช้ Embeddings ประสิทธิภาพสูงบน Local สำหรับทำ Vector
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # ผูกตัวแปลและฐานข้อมูลไว้ด้วยกันตลอด
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def add_documents(self, documents: List[Document]) -> None:
        """
        รับ List ของ LangChain Documents ที่หั่นมาจาก Phase 2 
        ไปแปลงความหมายและเซฟลงแฟ้มใน ChromaDB
        """
        if not documents:
            print("[Warning] ไม่มีก้อนข้อมูล (Chunks) สำหรับบันทึกลงในความจำเวกเตอร์")
            return
        
        print(f"[Log] กำลังแปลงข้อความให้ฝังเวกเตอร์ (Embedding) จำนวน {len(documents)} ก้อน ลงในตู้ ChromaDB...")
        # ฟังก์ชันนี้จะจัดการแปลงเวกเตอร์และเซฟลงไฟล์ดิสก์ท้องถิ่น (persist_directory) ให้อัตโนมัติใน Chroma V0.4+
        self.vector_store.add_documents(documents=documents)
        print("[Log] ประทับตราข้อมูลลง Vector Database สำเร็จ!")

    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        """
        ใช้สำหรับค้นหาข้อความที่มีมิติความหมายตรงกับคำถาม 
        
        Args:
            query (str): คำค้นหาหรือประโยคคำถาม
            k (int): จำนวนคำตอบ (Chunks) ที่คล้ายที่สุดที่ต้องการดึงออกมา
        """
        print(f"\n[Search] กำลังค้นหาคีย์เวิร์ด: '{query}'")
        results = self.vector_store.similarity_search(query, k=k)
        return results
