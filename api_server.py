import os
import shutil
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, AsyncGenerator

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Import core logic
from src.utils.document_loader import DocumentProcessor
from src.database.vector_store import Neo4jVectorStore
from src.database.graph_store import Neo4jGraphStore
from src.agents.graph_workflow import create_workflow
from src.agents.synthesizer_agent import SynthesizerAgent
from src.agents.router_agent import RouterAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.evaluator_agent import EvaluatorAgent

load_dotenv()

# --- Global State & Config ---
UPLOAD_DIR: str = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

indexing_logs: List[str] = []

def add_log(message: str) -> None:
    """บันทึก Log สำหรับการ Indexing"""
    global indexing_logs
    indexing_logs.append(message)
    if len(indexing_logs) > 50:
        indexing_logs.pop(0)

# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """จัดการการเปิด-ปิดทรัพยากรเมื่อแอปเริ่มและจบการทำงาน"""
    # Startup: สร้างโฟลเดอร์และตั้งค่าเบื้องต้น
    print("[LifeSpan] แอปพลิเคชันกำลังเริ่มต้น...")
    yield
    # Shutdown: ปิดการเชื่อมต่อต่างๆ (ถ้ามี)
    print("[LifeSpan] แอปพลิเคชันกำลังปิดตัวลง...")

app = FastAPI(
    title="Smart Document Assistant API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request/Response Models ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    route_decision: Optional[str] = None
    vector_context_count: int = 0
    graph_context_count: int = 0

# --- API Endpoints ---

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Smart Document Assistant API is running"}

@app.get("/api/indexing-status")
async def get_indexing_status() -> Dict[str, List[str]]:
    return {"logs": indexing_logs}

@app.get("/api/clear-logs")
async def clear_logs() -> Dict[str, str]:
    global indexing_logs
    indexing_logs = []
    return {"status": "success"}

@app.post("/api/upload-indexing")
async def upload_and_index(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """รับไฟล์ PDF และเริ่มกระบวนการหั่นข้อความ, สร้าง Vector และ Graph"""
    try:
        add_log(f"ได้รับไฟล์ทั้งหมด {len(files)} ไฟล์ เริ่มเตรียมการประมวลผล...")
        processor = DocumentProcessor()
        all_chunks = []
        
        # 1. บันทึกและประมวลผลไฟล์
        for i, file in enumerate(files):
            add_log(f"กำลังบันทึกและอ่านไฟล์ที่ {i+1}/{len(files)}: {file.filename}...")
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            chunks = processor.process_document(file_path)
            all_chunks.extend(chunks)
            add_log(f"ไฟล์ {file.filename} ประมวลผลเสร็จ (ได้ {len(chunks)} chunks)")
        
        if not all_chunks:
            raise HTTPException(status_code=400, detail="ไม่พบข้อความที่อ่านออกในเอกสาร")

        # 2. ล้างฐานข้อมูลเก่าก่อนเริ่มใหม่ (เพื่อให้ข้อมูลไม่ออกทะเล)
        graph_store = Neo4jGraphStore()
        with graph_store.driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            session.run("MATCH (n) DETACH DELETE n")
        add_log("ล้างฐานข้อมูลเดิมเรียบร้อย")

        # 3. สร้าง Vector Store ใน Neo4j
        add_log("กำลังประทับตรา Vector ลงใน Neo4j AuraDB...")
        vector_store = Neo4jVectorStore()
        vector_store.add_documents(all_chunks)
        add_log("บันทึก Vector สำเร็จ!")

        # 4. สร้าง Knowledge Graph ใน Neo4j
        add_log("เริ่มกระบวนการสร้าง Knowledge Graph...")
        graph_store.logger = add_log
        graph_store.process_and_save(all_chunks)
        add_log("ประมวลผล Knowledge Graph สำเร็จ!")

        return {
            "status": "success",
            "message": f"Successfully indexed {len(all_chunks)} chunks from {len(files)} files",
            "chunk_count": len(all_chunks)
        }
    except Exception as e:
        print(f"Error during indexing: {str(e)}")
        add_log(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat-stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """Endpoint สำหรับการแชทแบบสตรีมมิ่งโทเคน"""
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            router = RouterAgent()
            retriever = RetrieverAgent()
            synthesizer = SynthesizerAgent()
            
            state = {
                "question": request.message,
                "route_decision": "",
                "vector_context": [],
                "graph_context": [],
                "final_answer": ""
            }
            
            # Step 1: Routing
            route_state = router.route(state)
            state.update(route_state)
            yield f"data: {json.dumps({'type': 'status', 'value': 'AI ตัดสินใจเลือกเส้นทาง: ' + state['route_decision']})}\n\n"
            
            # Step 2: Retrieval
            if state["route_decision"] == "vector":
                state.update(retriever.retrieve_vector(state))
            elif state["route_decision"] == "graph":
                state.update(retriever.retrieve_graph(state))
            else:
                state.update(retriever.retrieve_vector(state))
                state.update(retriever.retrieve_graph(state))
            
            yield f"data: {json.dumps({'type': 'status', 'value': 'ดึงข้อมูล Context สำเร็จ กำลังเรียบเรียง...'})}\n\n"
            
            # Step 3: Metadata Prep
            sources = []
            seen_sources = set()
            for doc in state.get('vector_context', []):
                src = doc.metadata.get('source', 'Unknown')
                pg = doc.metadata.get('page', 1)
                full_src = f"{os.path.basename(src)}#page={pg}"
                if full_src not in seen_sources:
                    sources.append({'file': os.path.basename(src), 'page': pg})
                    seen_sources.add(full_src)

            metadata_payload = {
                'type': 'metadata', 
                'route': state['route_decision'], 
                'vectorCount': len(state.get('vector_context', [])), 
                'graphCount': len(state.get('graph_context', [])), 
                'sources': sources
            }
            yield f"data: {json.dumps(metadata_payload)}\n\n"
            
            # Step 4: Synthesis (Streaming)
            async for token in synthesizer.synthesize_stream(state):
                yield f"data: {json.dumps({'type': 'content', 'value': token})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/evaluate")
async def evaluate_endpoint(request: Dict[str, Any]) -> Dict[str, Any]:
    """ประเมินผลคำตอบของ AI ด้วย Ragas"""
    try:
        evaluator = EvaluatorAgent()
        result = evaluator.evaluate_response(
            request.get("question", ""),
            request.get("answer", ""),
            request.get("contexts", [])
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph-data")
async def get_graph_data() -> Dict[str, Any]:
    """ดึงข้อมูลกราฟทั้งหมดมาแสดงผลใน UI"""
    try:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        nodes, links = [], []
        with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            node_result = session.run("MATCH (n) RETURN n LIMIT 50")
            for record in node_result:
                n = record["n"]
                nodes.append({
                    "id": n.element_id, 
                    "label": list(n.labels)[0] if n.labels else "Entity", 
                    "properties": dict(n)
                })
            
            rel_result = session.run("""
                MATCH (n)-[r]->(m) 
                WHERE elementId(n) IN $node_ids AND elementId(m) IN $node_ids
                RETURN elementId(n) as source, elementId(m) as target, type(r) as type 
                LIMIT 100
            """, node_ids=[n['id'] for n in nodes])
            
            for record in rel_result:
                links.append({"source": record["source"], "target": record["target"], "type": record["type"]})
        
        driver.close()
        return {"nodes": nodes, "links": links}
    except Exception as e:
        return {"nodes": [], "links": [], "error": str(e)}

@app.get("/api/graph/neighbors/{node_id}")
async def get_node_neighbors(node_id: str) -> Dict[str, Any]:
    """ดึงโหนดเพื่อนบ้านเพื่อขยายกราฟใน UI"""
    try:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        nodes, links, seen_nodes = [], [], set()
        query = "MATCH (n) WHERE elementId(n) = $node_id MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 50"
        
        with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            result = session.run(query, node_id=node_id)
            for record in result:
                for k in ["n", "m"]:
                    node_obj = record[k]
                    nid = node_obj.element_id
                    if nid not in seen_nodes:
                        nodes.append({
                            "id": nid, 
                            "label": list(node_obj.labels)[0] if node_obj.labels else "Entity", 
                            "properties": dict(node_obj)
                        })
                        seen_nodes.add(nid)
                links.append({
                    "source": record["n"].element_id, 
                    "target": record["m"].element_id, 
                    "type": record["r"].type if hasattr(record["r"], 'type') else "RELATED_TO"
                })
        driver.close()
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount โฟลเดอร์เพื่อให้อ้างอิงไฟล์ PDF ได้
app.mount("/pdf-files", StaticFiles(directory="uploads"), name="pdf-files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
