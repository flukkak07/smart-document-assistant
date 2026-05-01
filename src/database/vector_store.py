import os
from typing import List, Optional
from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

class Neo4jVectorStore:
    """
    คลาสสำหรับจัดการ Vector Database บน Neo4j AuraDB (Cloud)
    ใช้สำหรับจัดเก็บและค้นหาข้อมูลเชิงความหมาย (Semantic Search) แทนที่ ChromaDB
    
    Attributes:
        embeddings (HuggingFaceEndpointEmbeddings): อินสแตนซ์สำหรับเรียกใช้ Embedding API
        url (str): URL ของ Neo4j AuraDB
        username (str): ชื่อผู้ใช้งาน Neo4j
        password (str): รหัสผ่าน Neo4j
        index_name (str): ชื่อของ Vector Index ในฐานข้อมูล
        vector_store (Optional[Neo4jVector]): อินสแตนซ์ของ LangChain Neo4jVector
    """

    def __init__(self) -> None:
        """
        เริ่มต้นการเชื่อมต่อและตั้งค่าพื้นฐานสำหรับ Vector Store
        """
        # 1. ตั้งค่า Embeddings ผ่าน HuggingFace API
        hf_token: Optional[str] = os.getenv("HUGGINGFACE_API_TOKEN")
        model_name: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        
        if not hf_token:
            print("[Warning] ไม่พบ HUGGINGFACE_API_TOKEN ใน Environment Variables")
            
        self.embeddings = HuggingFaceEndpointEmbeddings(
            model=model_name,
            huggingfacehub_api_token=hf_token
        )
        
        # 2. ตั้งค่าการเชื่อมต่อฐานข้อมูล
        self.url: Optional[str] = os.getenv("NEO4J_URI")
        self.username: str = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password: Optional[str] = os.getenv("NEO4J_PASSWORD")
        self.index_name: str = "vector_index" 

        self.vector_store: Optional[Neo4jVector] = None

    def _initialize_store(self) -> Neo4jVector:
        """
        สร้างหรือดึงอินสแตนซ์ของ Neo4jVector (Internal use)
        
        Returns:
            Neo4jVector: อินสแตนซ์ที่พร้อมใช้งานสำหรับการค้นหาหรือเพิ่มข้อมูล
        """
        if self.vector_store is None:
            self.vector_store = Neo4jVector(
                embedding=self.embeddings,
                url=self.url,
                username=self.username,
                password=self.password,
                index_name=self.index_name,
                search_type="hybrid" # ใช้ Hybrid Search (Vector + Full-text) เพื่อความแม่นยำ
            )
        return self.vector_store

    def add_documents(self, documents: List[Document]) -> None:
        """
        นำรายการเอกสาร (Chunks) ไปแปลงเป็น Vector และบันทึกลงใน Neo4j AuraDB
        
        Args:
            documents (List[Document]): รายการก้อนข้อมูลที่ต้องการบันทึก
        """
        if not documents:
            print("[Warning] รายการเอกสารว่างเปล่า ข้ามขั้นตอนการบันทึก Vector")
            return
        
        print(f"[Log] กำลังส่ง {len(documents)} chunks ไปยัง Neo4j Vector Index...")
        
        # ใช้ from_documents เพื่อสร้าง/อัปเดต Index และบันทึกข้อมูล
        self.vector_store = Neo4jVector.from_documents(
            documents=documents,
            embedding=self.embeddings,
            url=self.url,
            username=self.username,
            password=self.password,
            index_name=self.index_name
        )
        print("[Log] บันทึกข้อมูลลง Neo4j Vector Store สำเร็จ")

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        ค้นหาเอกสารที่มีความหมายใกล้เคียงกับคำถามมากที่สุด
        
        Args:
            query (str): คำถามหรือข้อความที่ต้องการค้นหา
            k (int, optional): จำนวนผลลัพธ์ที่ต้องการ. Defaults to 5.
            
        Returns:
            List[Document]: รายการเอกสารที่ค้นพบ
        """
        if not query.strip():
            return []
            
        print(f"[Search] กำลังค้นหาข้อมูลที่เกี่ยวข้องกับ: '{query}'")
        store = self._initialize_store()
        results: List[Document] = store.similarity_search(query, k=k)
        return results
