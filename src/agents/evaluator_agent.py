import os
import numpy as np
from typing import List, Dict
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

class EvaluatorAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def evaluate_response(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """
        ประเมินคุณภาพของคำตอบ พร้อมรองรับรูปแบบข้อมูลจาก Ragas ผลลัพธ์
        """
        print(f"\n[Evaluator] 🔍 เริ่มการประเมินผลสำหรับคำถาม: {question[:50]}...")
        
        try:
            # ตั้งค่าเมตริก
            faithfulness.llm = self.llm
            answer_relevancy.llm = self.llm
            answer_relevancy.embeddings = self.embeddings
            
            # เตรียมข้อมูล
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
            
            # ดึงคะแนน (รองรับทั้งแบบ scalar และ list)
            raw_f = result["faithfulness"]
            raw_r = result["answer_relevancy"]
            
            f_score = raw_f[0] if isinstance(raw_f, (list, np.ndarray)) else raw_f
            r_score = raw_r[0] if isinstance(raw_r, (list, np.ndarray)) else raw_r
            
            print(f"[Evaluator] ✅ ประเมินสำเร็จ! ได้คะแนนจริง: F={f_score}, R={r_score}")
            
            return {
                "faithfulness": float(f_score) if not np.isnan(f_score) else 0.0,
                "answer_relevancy": float(r_score) if not np.isnan(r_score) else 0.0,
                "status": "success"
            }
        except Exception as e:
            print(f"[Evaluator] ❌ เกิดข้อผิดพลาดระหว่างประเมิน: {str(e)}")
            return {"status": "error", "message": str(e), "faithfulness": 0.0, "answer_relevancy": 0.0}
