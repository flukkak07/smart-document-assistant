import os
import numpy as np
from typing import List, Dict, Any
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceInferenceAPIEmbeddings
from dotenv import load_dotenv

load_dotenv()

class EvaluatorAgent:
    """
    เอเจนท์ผู้ประเมินผล (Evaluator) ทำหน้าที่ตรวจสอบความถูกต้อง (Faithfulness)
    และความเกี่ยวข้อง (Relevancy) ของคำตอบโดยใช้ Ragas Framework
    
    Attributes:
        llm (ChatGroq): LLM สำหรับการประเมิน (ใช้รุ่นใหญ่ 70B เพื่อความแม่นยำ)
        embeddings (HuggingFaceInferenceAPIEmbeddings): เวกเตอร์สำหรับคำนวณความ relevancy
    """

    def __init__(self) -> None:
        """เริ่มต้นการตั้งค่า Evaluator Agent"""
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # ใช้ Embeddings API แบบเดียวกับ Vector Store
        self.embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=os.getenv("HUGGINGFACE_API_TOKEN"),
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )

    def evaluate_response(self, question: str, answer: str, contexts: List[str]) -> Dict[str, Any]:
        """
        ประเมินคุณภาพของคำตอบเทียบกับคำถามและบริบทอ้างอิง
        
        Args:
            question (str): คำถามของผู้ใช้
            answer (str): คำตอบที่ระบบสร้างขึ้น
            contexts (List[str]): รายการบริบทที่ใช้ประกอบการตอบ
            
        Returns:
            Dict[str, Any]: คะแนนการประเมินและสถานะ
        """
        if not contexts:
            return {"status": "skipped", "message": "No context provided for evaluation", "faithfulness": 0.0, "answer_relevancy": 0.0}

        print(f"\n[Evaluator] 🔍 เริ่มการประเมินผลสำหรับคำถาม: {question[:50]}...")
        
        try:
            # กำหนดโมเดลให้กับ Metrics ของ Ragas
            faithfulness.llm = self.llm
            answer_relevancy.llm = self.llm
            answer_relevancy.embeddings = self.embeddings
            
            # เตรียมข้อมูลสำหรับ Ragas Dataset
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts]
            }
            dataset = Dataset.from_dict(data)
            
            # รันการประเมิน
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy],
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # ดึงคะแนนและจัดการกับรูปแบบข้อมูลที่อาจมาเป็น list
            raw_f = result["faithfulness"]
            raw_r = result["answer_relevancy"]
            
            f_score = raw_f[0] if isinstance(raw_f, (list, np.ndarray)) else raw_f
            r_score = raw_r[0] if isinstance(raw_r, (list, np.ndarray)) else raw_r
            
            # ตรวจสอบค่า NaN
            f_score = float(f_score) if not np.isnan(f_score) else 0.0
            r_score = float(r_score) if not np.isnan(r_score) else 0.0
            
            print(f"[Evaluator] ✅ ประเมินสำเร็จ! คะแนน: Faithfulness={f_score:.2f}, Relevancy={r_score:.2f}")
            
            return {
                "faithfulness": f_score,
                "answer_relevancy": r_score,
                "status": "success"
            }
        except Exception as e:
            print(f"[Evaluator] ❌ เกิดข้อผิดพลาด: {str(e)}")
            return {"status": "error", "message": str(e), "faithfulness": 0.0, "answer_relevancy": 0.0}
