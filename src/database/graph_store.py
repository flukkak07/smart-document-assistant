import os
from typing import List, Optional, Callable
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase, Driver
from langchain_core.documents import Document

load_dotenv()

class KnowledgeRelation(BaseModel):
    """นิยามโครงสร้างความสัมพันธ์ของข้อมูล"""
    source_entity: str = Field(description="ชื่อสิ่งของ/บุคคลต้นทาง (ภาษาไทย)")
    source_type: str = Field(description="ประเภทของ Entity ต้นทาง (ภาษาอังกฤษตัวพิมพ์ใหญ่)")
    relationship: str = Field(description="ความสัมพันธ์กริยา (ภาษาอังกฤษตัวพิมพ์ใหญ่)")
    target_entity: str = Field(description="ชื่อสิ่งของ/บุคคลปลายทาง (ภาษาไทย)")
    target_type: str = Field(description="ประเภทของ Entity ปลายทาง (ภาษาอังกฤษตัวพิมพ์ใหญ่)")

class KnowledgeGraph(BaseModel):
    """โครงสร้างรายการความสัมพันธ์ที่สกัดได้"""
    relations: List[KnowledgeRelation] = Field(description="รายการความสัมพันธ์ทั้งหมด")

class Neo4jGraphStore:
    """
    คลาสสำหรับจัดการ Knowledge Graph บน Neo4j AuraDB
    ทำหน้าที่สกัดความสัมพันธ์จากข้อความด้วย LLM และบันทึกลงใน Graph Database
    
    Attributes:
        driver (Driver): Neo4j Driver สำหรับเชื่อมต่อฐานข้อมูล
        llm (ChatGroq): อินสแตนซ์ของ LLM สำหรับการสกัดข้อมูล
        extractor (Callable): ฟังก์ชันสำหรับสกัดข้อมูลตามโครงสร้างที่กำหนด
        logger (Optional[Callable]): ฟังก์ชันสำหรับส่ง Log ไปยัง UI
    """

    def __init__(self) -> None:
        """
        เริ่มต้นการเชื่อมต่อ Neo4j และตั้งค่า LLM Chain
        """
        # 1. เชื่อมต่อ Neo4j Cloud
        uri: Optional[str] = os.getenv("NEO4J_URI")
        user: str = os.getenv("NEO4J_USERNAME", "neo4j")
        password: Optional[str] = os.getenv("NEO4J_PASSWORD")
        
        if not uri or not password:
            print("[Warning] ข้อมูลการเชื่อมต่อ Neo4j ไม่ครบถ้วนใน .env")
            
        print(f"[Log] กำลังเชื่อมต่อ Neo4j Graph ที่: {uri}")
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # 2. ตั้งค่า LLM (Groq) เพื่อใช้สกัดข้อมูล
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=2048,
        )
        
        # 3. เตรียม Prompt และ Chain สำหรับการสกัดความสัมพันธ์
        self.extractor = self.llm.with_structured_output(KnowledgeGraph)
        self.logger: Optional[Callable[[str], None]] = None
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือผู้เชี่ยวชาญด้าน Data Extraction จากเอกสารภาษาไทย 
หน้าที่ของคุณคือ สกัด "ความสัมพันธ์" เป็นคู่ๆ จากข้อความที่ให้มา
โดยแปลงออกมาให้ตรงตาม Schema ที่กำหนด เงื่อนไขสำคัญคือ:
1. source_type และ target_type จะต้องเป็นภาษาอังกฤษตัวพิมพ์ใหญ่ เช่น PERSON, ORGANIZATION, ROLE, SKILL
2. relationship ให้เป็นคำกริยาภาษาอังกฤษตัวพิมพ์ใหญ่แบบติดกัน เช่น WORKS_AT, HAS_SKILL, INCLUDES
3. ชื่อ Entity (source_entity, target_entity) ให้เป็นคำภาษาไทยแบบสั้นกระชับที่สุด
หากไม่มีความสัมพันธ์ที่ชัดเจน ไม่ต้องสุ่มสร้างขึ้นมา"""),
            ("human", "ข้อความสำหรับการสกัด:\n{text}")
        ])
        
        self.chain = self.prompt | self.extractor

    def process_and_save(self, chunks: List[Document]) -> None:
        """
        ประมวลผลก้อนข้อมูล (Chunks) เพื่อสกัดความสัมพันธ์และบันทึกลงฐานข้อมูล
        
        Args:
            chunks (List[Document]): รายการก้อนข้อมูลที่ต้องการประมวลผล
        """
        print(f"\n[Graph Indexing] เริ่มสกัดความสัมพันธ์จาก {len(chunks)} Chunks...")
        
        for i, chunk in enumerate(chunks):
            status_msg = f"กำลังวิเคราะห์ Chunk {i+1}/{len(chunks)}..."
            print(status_msg)
            if self.logger: 
                self.logger(status_msg)
                
            try:
                # เรียกใช้ LLM เพื่อสกัดข้อมูล
                graph_data = self.chain.invoke({"text": chunk.page_content})
                
                if graph_data and graph_data.relations:
                    self._save_relations(graph_data.relations)
                    success_msg = f"  + บันทึกแล้ว {len(graph_data.relations)} ความสัมพันธ์"
                    print(success_msg)
                    if self.logger: self.logger(success_msg)
                else:
                    print(f"  - ไม่พบความสัมพันธ์ที่ชัดเจนใน Chunk {i+1}")
                    
            except Exception as e:
                error_msg = f"[Error] การสกัดข้อมูลใน Chunk {i+1} ล้มเหลว: {str(e)}"
                print(error_msg)
                if self.logger: self.logger(error_msg)

    def _save_relations(self, relations: List[KnowledgeRelation]) -> None:
        """
        บันทึกข้อมูลความสัมพันธ์ลงใน Neo4j (Internal use)
        
        Args:
            relations (List[KnowledgeRelation]): รายการความสัมพันธ์ที่สกัดได้
        """
        for rel in relations:
            # คลีนข้อมูล Label และ Relationship Name
            s_type = rel.source_type.replace(" ", "_").upper()
            t_type = rel.target_type.replace(" ", "_").upper()
            r_name = rel.relationship.replace(" ", "_").upper()
            
            if not s_type or not t_type or not r_name:
                continue
                
            # ใช้ MERGE เพื่อป้องกันข้อมูลซ้ำซ้อน
            query = f"""
            MERGE (a:{s_type} {{id: $s_name}})
            MERGE (b:{t_type} {{id: $t_name}})
            MERGE (a)-[r:{r_name}]->(b)
            """
            
            params = {
                "s_name": rel.source_entity.strip(),
                "t_name": rel.target_entity.strip(),
            }
            
            with self.driver.session() as session:
                session.run(query, **params)

    def close(self) -> None:
        """ปิดการเชื่อมต่อฐานข้อมูล"""
        if self.driver:
            self.driver.close()
