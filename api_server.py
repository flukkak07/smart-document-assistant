import os
import shutil
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our core logic
from src.utils.document_loader import DocumentProcessor
from src.database.vector_store import ChromaVectorStore
from src.database.graph_store import Neo4jGraphStore
from src.agents.graph_workflow import create_workflow
from src.agents.synthesizer_agent import SynthesizerAgent
from src.agents.router_agent import RouterAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.evaluator_agent import EvaluatorAgent

load_dotenv()

app = FastAPI(title="Smart Document Assistant API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent storage for PDFs
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Global variables for state management
workflow_app = create_workflow()
indexing_logs = []

def add_log(message: str):
    global indexing_logs
    indexing_logs.append(message)
    if len(indexing_logs) > 50:
        indexing_logs.pop(0)

# --- Models ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    route_decision: Optional[str] = None
    vector_context_count: int = 0
    graph_context_count: int = 0

# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Smart Document Assistant API is running"}

@app.get("/api/indexing-status")
async def get_indexing_status():
    return {"logs": indexing_logs}

@app.get("/api/clear-logs")
async def clear_logs():
    global indexing_logs
    indexing_logs = []
    return {"status": "success"}

@app.post("/api/upload-indexing")
async def upload_and_index(files: List[UploadFile] = File(...)):
    try:
        add_log(f"ได้รับไฟล์ทั้งหมด {len(files)} ไฟล์ เริ่มเตรียมการประมวลผล...")
        processor = DocumentProcessor()
        all_chunks = []
        for i, file in enumerate(files):
            add_log(f"กำลังบันทึกและอ่านไฟล์ที่ {i+1}/{len(files)}: {file.filename}...")
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            chunks = processor.process_document(file_path)
            all_chunks.extend(chunks)
            add_log(f"ไฟล์ {file.filename} ประมวลผลเสร็จ (ได้ {len(chunks)} chunks)")
        
        if not all_chunks:
            raise HTTPException(status_code=400, detail="No readable text found in documents")

        add_log(f"กำลังหั่นข้อมูลได้ {len(all_chunks)} ส่วน...")
        vector_store = ChromaVectorStore()
        vector_store.vector_store.delete_collection()
        vector_store = ChromaVectorStore()
        add_log("กำลังประทับตรา Vector ลงใน ChromaDB...")
        vector_store.add_documents(all_chunks)
        add_log("บันทึก Vector สำเร็จ!")

        add_log("เริ่มกระบวนการสร้าง Knowledge Graph...")
        graph_store = Neo4jGraphStore()
        graph_store.logger = add_log
        with graph_store.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        graph_store.process_and_save(all_chunks)
        add_log("ประมวลผล Knowledge Graph สำเร็จ!")

        global workflow_app
        workflow_app = create_workflow()

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
async def chat_stream_endpoint(request: ChatRequest):
    async def event_generator():
        try:
            router = RouterAgent()
            retriever = RetrieverAgent()
            synthesizer = SynthesizerAgent()
            state = {"question": request.message, "route_decision": "", "vector_context": [], "graph_context": [], "final_answer": ""}
            
            route_state = router.route(state)
            state.update(route_state)
            route_desc = state["route_decision"]
            yield f"data: {json.dumps({'type': 'status', 'value': f'AI ตัดสินใจเลือกเส้นทาง: {route_desc}'})}\n\n"
            
            if state["route_decision"] == "vector":
                state.update(retriever.retrieve_vector(state))
            elif state["route_decision"] == "graph":
                state.update(retriever.retrieve_graph(state))
            else:
                state.update(retriever.retrieve_vector(state))
                state.update(retriever.retrieve_graph(state))
            
            yield f"data: {json.dumps({'type': 'status', 'value': 'ดึงข้อมูล Context สำเร็จ กำลังเรียบเรียง...'})}\n\n"
            
            sources = []
            seen_sources = set()
            for doc in state.get('vector_context', []):
                src = doc.metadata.get('source', 'Unknown')
                pg = doc.metadata.get('page', 1)
                full_src = f"{src}#page={pg}"
                if full_src not in seen_sources:
                    sources.append({'file': os.path.basename(src), 'page': pg})
                    seen_sources.add(full_src)

            yield f"data: {json.dumps({'type': 'metadata', 'route': state['route_decision'], 'vectorCount': len(state.get('vector_context', [])), 'graphCount': len(state.get('graph_context', [])), 'sources': sources, 'contexts': [doc.page_content for doc in state.get('vector_context', [])[:5]]})}\n\n"
            
            async for token in synthesizer.synthesize_stream(state):
                yield f"data: {json.dumps({'type': 'content', 'value': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/evaluate")
async def evaluate_endpoint(request: Dict):
    try:
        evaluator = EvaluatorAgent()
        result = evaluator.evaluate_response(
            request.get("question"),
            request.get("answer"),
            request.get("contexts", [])
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph-data")
async def get_graph_data():
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        nodes, links = [], []
        with driver.session() as session:
            # โหลดโหนดเบื้องต้นจำกัดที่ 50
            node_result = session.run("MATCH (n) RETURN n LIMIT 50")
            for record in node_result:
                n = record["n"]
                nodes.append({"id": n.element_id, "label": list(n.labels)[0] if n.labels else "Entity", "properties": dict(n)})
            
            # โหลดความสัมพันธ์
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
async def get_node_neighbors(node_id: str):
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        nodes, links, seen_nodes = [], [], set()
        # ค้นหาโดยใช้ elementId กู้คืนความสัมพันธ์
        query = "MATCH (n) WHERE elementId(n) = $node_id MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 50"
        with driver.session() as session:
            result = session.run(query, node_id=node_id)
            for record in result:
                for k in ["n", "m"]:
                    node_obj = record[k]
                    nid = node_obj.element_id
                    if nid not in seen_nodes:
                        nodes.append({"id": nid, "label": list(node_obj.labels)[0] if node_obj.labels else "Entity", "properties": dict(node_obj)})
                        seen_nodes.add(nid)
                links.append({"source": record["n"].element_id, "target": record["m"].element_id, "type": record["r"].type if hasattr(record["r"], 'type') else "RELATED_TO"})
        driver.close()
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph/node-details/{node_id}")
async def get_graph_node_details(node_id: str):
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        node_info = {"label": "Entity", "properties": {}}
        search_query = node_id
        with driver.session() as session:
            result = session.run("MATCH (n) WHERE elementId(n) = $node_id RETURN n LIMIT 1", node_id=node_id)
            record = result.single()
            if record:
                n = record["n"]
                node_info["label"] = list(n.labels)[0] if n.labels else "Entity"
                node_info["properties"] = dict(n)
                # ใช้ชื่อของ Entity สำหรับการค้นหาใน Vector Store
                search_query = node_info["properties"].get("id", node_id)
        driver.close()

        from src.database.vector_store import ChromaVectorStore
        vector_store = ChromaVectorStore()
        chunks = vector_store.similarity_search(search_query, k=5)
        
        sources = []
        for doc in chunks:
            sources.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
            
        return {
            "node": node_info,
            "sources": sources
        }
    except Exception as e:
        print(f"Error fetching node details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/pdf-files", StaticFiles(directory="uploads"), name="pdf-files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
鼓
