import os
import numpy as np
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

def debug_evaluation():
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # ใช้ข้อมูลจากคำถามล่าสุดของคุณ
    question = "อธิบายสรุปใจความสำคัญของเอกสารทั้งหมดในมุมมองเชิงธุรกิจ"
    answer = """เอกสารนี้เกี่ยวข้องกับเทคนิคการทำความสะอาดในอาคารและบ้าน โดยมีจุดมุ่งหมายเพื่อให้สถานที่ทำงานและที่อยู่น่าอยู่... ประโยชน์ของการทำความสะอาดรวมถึง: ทำให้ที่ทำงานน่าน่าอยู่, ช่วยลดปัญหาเชื้อโรคและแบคทีเรีย, ทำให้สมาชิกในกลุ่มมีความรู้และทัศนคติที่ดีต่อการทำความสะอาด"""
    contexts = ["การทำความสะอาดเป็นกิจกรรมที่สำคัญในการรักษาสภาพแวดล้อมที่ดีและเพิ่มประสิทธิภาพการทำงาน เทคนิคการทำความสะอาดรวมถึงการใช้น้ำยาที่เหมาะสมและการจัดการรอยเปื้อนอย่างมีประสิทธิภาพ เพื่อสุขอนามัยที่ดีในองค์กร"]

    data = {
        "question": [question],
        "answer": [answer],
        "contexts": [contexts]
    }
    dataset = Dataset.from_dict(data)

    print("--- Debugging Ragas Evaluation ---")
    print(f"Question: {question[:50]}...")
    print(f"Answer Context Length: {len(answer)}")
    
    # ตั้งค่า metrics
    faithfulness.llm = llm
    answer_relevancy.llm = llm
    answer_relevancy.embeddings = embeddings

    try:
        print("Running evaluate...")
        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
        print("Result:", result)
        
        f_val = result["faithfulness"]
        r_val = result["answer_relevancy"]
        
        print(f"Faithfulness Raw: {f_val}")
        print(f"Relevancy Raw: {r_val}")
        
    except Exception as e:
        print(f"Error during debug: {str(e)}")

if __name__ == "__main__":
    debug_evaluation()
鼓
