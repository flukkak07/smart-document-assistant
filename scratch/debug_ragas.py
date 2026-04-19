import os
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    temperature=0,
    model_name="llama-3.1-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY")
)

data = {
    "question": ["What is graphRAG?"],
    "answer": ["GraphRAG is a retrieval augmented generation technique that uses knowledge graphs."],
    "contexts": [["Knowledge graphs are used in RAG to represent relationships between entities. GraphRAG improves retrieval."]]
}
dataset = Dataset.from_dict(data)

try:
    print("Starting evaluation...")
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=llm
    )
    print("Evaluation result type:", type(result))
    print("Evaluation result content:", result)
    print("Faithfulness score:", result["faithfulness"])
except Exception as e:
    print("Error:", str(e))
