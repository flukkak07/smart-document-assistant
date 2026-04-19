import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase
from langchain_core.documents import Document

# โหลดค่าคอนฟิก 
load_dotenv()

# ==========================================
# 1. นิยามโครงสร้าง Pydantic สำหรับบังคับให้ AI โยน JSON ที่มีระเบียบมาให้เรา
# ==========================================
class KnowledgeRelation(BaseModel):
    source_entity: str = Field(description="ชื่อสิ่งของ/บุคคลต้นทาง (ภาษาไทย) เช่น เคน, มหาวิทยาลัยเกษตรศาสตร์")
    source_type: str = Field(description="ประเภทของ Entity ต้นทาง เช่น PERSON, ORGANIZATION, LOCATION")
    relationship: str = Field(description="ความสัมพันธ์กริยาภาษาอังกฤษตัวพิมพ์ใหญ่ เช่น WORKS_AT, STUDIES")
    target_entity: str = Field(description="ชื่อสิ่งของ/บุคคลปลายทาง (ภาษาไทย) เช่น คณะวิทยาศาสตร์")
    target_type: str = Field(description="ประเภทของ Entity ปลายทาง เช่น ORGANIZATION, LOCATION")

class KnowledgeGraph(BaseModel):
    relations: List[KnowledgeRelation] = Field(description="รายการความสัมพันธ์ทั้งหมดที่สกัดมาจากข้อความ")


# ==========================================
# 2. คลาสหลักสำหรับการวาดกราฟความสัมพันธ์
# ==========================================
class Neo4jGraphStore:
    """
    คลาสรับหน้าที่รับ Chunk มาตีความหาคู่หู Entity ผ่าน LLM
    ก่อนจะสร้าง Cypher Query และวาดลงกระดานฐานข้อมูล 
    """
    def __init__(self):
        # 1. เชื่อมต่อฐานข้อมูลด้วย Neo4j Driver แท้ (หลบเลี่ยง LangChain Neo4j APOC)
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
        )
        
        # 2. เชื่อมต่อ LLM อัจฉริยะ (ใช้โหมดแบบไม่สร้างสรรค์ เพื่อเน้นสกัดข้อมูลแฟคท์)
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=2048,
        )
        
        # 3. ผูก LLM เข้ากับฟังก์ชันวิเคราะห์ Pydantic ข้อมูลจะได้ไม่เบี้ยว
        self.extractor = self.llm.with_structured_output(KnowledgeGraph)
        self.logger = None  # จะถูกตั้งค่าโดย API Server
        
        # 4. Prompt พลังสูง สั่งการ AI ดึงความสัมพันธ์แบบชัดเจน
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือผู้เชี่ยวชาญด้าน Data Extraction จากเอกสารภาษาไทย 
หน้าที่ของคุณคือ สกัด "ความสัมพันธ์" เป็นคู่ๆ จากข้อความที่ให้มา
โดยแปลงออกมาให้ตรงตาม Schema ที่กำหนด เงื่อนไขสำคัญคือ:
1. source_type และ target_type จะต้องเป็นภาษาอังกฤษตัวพิมพ์ใหญ่ เช่น PERSON, ORGANIZATION, ROLE, SKILL
2. relationship ให้เป็นคำกริยาภาษาอังกฤษตัวพิมพ์ใหญ่แบบติดกัน เช่น WORKS_AT, HAS_SKILL, INCLUDES
3. ชื่อ Entity (source_entity, target_entity) ให้เป็นคำภาษาไทยแบบสั้นกระชับที่สุด ตามตัวอักษรของจริง ไม่เอาประโยคยาวๆ
หากไม่มีความสัมพันธ์ที่ชัดเจน ไม่ต้องสุ่มสร้างขึ้นมา"""),
            ("human", "ข้อความ:\n{text}")
        ])
        
        self.chain = self.prompt | self.extractor

    def process_and_save(self, chunks: List[Document]) -> None:
        """
        สกัดข้อความทีละ Chunk แล้วบันทึกลง Neo4j ทันที
        """
        print(f"\n[Log] เตรียมสกัดและบันทึก Knowledge Graph จาก {len(chunks)} Chunks")
        
        for i, chunk in enumerate(chunks):
            msg = f"กำลังประมวลผล Chunk {i+1}/{len(chunks)} ด้วย LLM..."
            print(msg)
            if self.logger: self.logger(msg)
            try:
                # ให้ AI วิเคราะห์โครงสร้าง
                graph_data = self.chain.invoke({"text": chunk.page_content})
                
                # นำข้อมูลที่ได้ มาแปลงเป็น Cypher ยิงเข้าฐาน
                if graph_data and graph_data.relations:
                    self._save_to_neo4j(graph_data.relations)
                    msg = f"  + ภารกิจสำเร็จ: วาด {len(graph_data.relations)} เส้นความสัมพันธ์ลง Neo4j"
                    print(msg)
                    if self.logger: self.logger(msg)
                else:
                    msg = f"  - ข้าม: ไม่พบความแข็งแรงของความสัมพันธ์ที่ชัดเจนในก้อนนี้ (Chunk {i+1})"
                    print(msg)
                    if self.logger: self.logger(msg)
                    
            except Exception as e:
                print(f"[Error] Chunk {i+1} ขัดข้องระหว่างการแยกแยะ: {e}")

    def _save_to_neo4j(self, relations: List[KnowledgeRelation]) -> None:
        """
        แปลงข้อมูล Object ให้กลายเป็นภาษา Cypher ของ Neo4j (ใช้ MERGE ป้องกันข้อมูลซ้ำ)
        """
        for rel in relations:
            # คลีนชื่อประเภทให้ปลอดภัยสำหรับการเป็น Label
            s_type = rel.source_type.replace(" ", "_").upper()
            t_type = rel.target_type.replace(" ", "_").upper()
            r_name = rel.relationship.replace(" ", "_").upper()
            
            if not s_type or not t_type or not r_name:
                continue
                
            # คำสั่ง Cypher 
            # (MERGE a) คือสร้าง/หาโหนด a
            # (MERGE b) คือสร้าง/หาโหนด b
            # (MERGE a->b) เพื่อจับคู่
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
