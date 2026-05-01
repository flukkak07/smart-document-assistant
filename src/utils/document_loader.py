import os
import fitz  # PyMuPDF
import base64
import io
from typing import List, Optional
from PIL import Image
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

class DocumentProcessor:
    """
    คลาสสำหรับประมวลผลเอกสาร PDF ทั้งแบบข้อความปกติและแบบสแกน (OCR)
    โดยใช้ Groq Vision API สำหรับการทำ OCR แทน Tesseract เพื่อรองรับการทำงานบน Cloud
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        เริ่มต้นการตั้งค่าสำหรับการหั่นข้อความและเชื่อมต่อกับ Vision AI
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # ตั้งค่าโมเดล Vision สำหรับทำ OCR
        self.vision_model = ChatGroq(
            model="llama-3.2-11b-vision-preview",
            temperature=0.0
        )

    def _ocr_with_vision_ai(self, file_path: str) -> List[Document]:
        """
        ใช้ Vision AI ในการอ่านข้อความจากไฟล์ PDF (โหมด OCR)
        โดยการแปลงหน้า PDF เป็นรูปภาพและส่งให้ AI วิเคราะห์
        
        Args:
            file_path (str): พาธของไฟล์ PDF
            
        Returns:
            List[Document]: รายการเอกสารที่สกัดข้อความออกมาแล้ว
        """
        print(f"[Vision OCR] กำลังวิเคราะห์เอกสารด้วย AI: {os.path.basename(file_path)}...")
        doc = fitz.open(file_path)
        documents: List[Document] = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # แปลงหน้า PDF เป็นรูปภาพ (Base64)
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("jpg")
            base64_image = base64.b64encode(img_data).decode('utf-8')
            
            try:
                # ส่งภาพให้ Groq Vision อ่าน
                prompt = "Extract all text from this document image accurately. The text is in Thai and English. Return only the extracted text without any explanations."
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ]
                )
                
                response = self.vision_model.invoke([message])
                text = response.content.strip()
                
                if text:
                    doc_metadata = {"source": file_path, "page": page_num + 1}
                    documents.append(Document(page_content=text, metadata=doc_metadata))
                    print(f"  + อ่านหน้าที่ {page_num + 1} สำเร็จ")
                
            except Exception as e:
                print(f"[Error] พบข้อผิดพลาดในหน้าที่ {page_num + 1}: {str(e)}")
                
        doc.close()
        return documents

    def load_pdf(self, file_path: str) -> List[Document]:
        """
        โหลดไฟล์ PDF และตรวจสอบว่าต้องใช้โหมด OCR หรือไม่
        
        Args:
            file_path (str): พาธของไฟล์ PDF
            
        Returns:
            List[Document]: ข้อมูลเนื้อหาในแต่ละหน้า
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ไม่พบไฟล์: {file_path}")

        # ขั้นแรก: ลองโหลดแบบปกติ (Digital PDF)
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # ตรวจสอบความยาวข้อความรวมเพื่อประเมินว่าเป็นไฟล์แสกนหรือไม่
        total_text = "".join([d.page_content.strip() for d in documents])
        
        if len(total_text) < 100:
            print(f"[Warning] ตรวจพบไฟล์แสกนหรือข้อความน้อยผิดปกติ กำลังสลับไปใช้ Vision OCR...")
            documents = self._ocr_with_vision_ai(file_path)
            
        return documents

    def process_document(self, file_path: str) -> List[Document]:
        """
        โหลดและหั่นเอกสารเป็นก้อน (Chunks) พร้อมใช้งาน
        
        Args:
            file_path (str): พาธของไฟล์ PDF
            
        Returns:
            List[Document]: รายการ Chunks ที่หั่นเรียบร้อยแล้ว
        """
        print(f"[Log] เริ่มประมวลผลไฟล์: {os.path.basename(file_path)}")
        documents = self.load_pdf(file_path)
        
        # กรองเอาเฉพาะหน้าที่มีข้อความ
        valid_docs = [doc for doc in documents if doc.page_content.strip()]
        
        if not valid_docs:
            print("[Failed] ไม่พบข้อความในเอกสารนี้")
            return []
            
        print(f"[Log] อ่านเสร็จสิ้น ({len(valid_docs)} หน้า) กำลังหั่นเป็น Chunks...")
        chunks = self.text_splitter.split_documents(valid_docs)
        
        print(f"[Log] ประมวลผลสำเร็จ ได้ {len(chunks)} chunks")
        return chunks

    def process_directory(self, folder_path: str) -> List[Document]:
        """
        ประมวลผลไฟล์ PDF ทั้งหมดในโฟลเดอร์ที่กำหนด
        
        Args:
            folder_path (str): พาธของโฟลเดอร์
            
        Returns:
            List[Document]: รายการ Chunks ทั้งหมดจากทุกไฟล์
        """
        all_chunks: List[Document] = []
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            return all_chunks

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(".pdf"):
                full_path = os.path.join(folder_path, filename)
                chunks = self.process_document(full_path)
                all_chunks.extend(chunks)
                
        return all_chunks

if __name__ == "__main__":
    # สำหรับทดสอบการทำงานเบื้องต้น
    processor = DocumentProcessor()
    # ใส่พาธไฟล์ทดสอบที่นี่
    # chunks = processor.process_document("path/to/your/test.pdf")
    # print(f"Total chunks: {len(chunks)}")
