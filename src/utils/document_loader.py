import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from typing import List
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# โหลดค่าคอนฟิกเพื่อตรวจสอบว่ามีพาท Tesseract หรือไม่
load_dotenv()
# เช็คใน .env ก่อน ถ้าไม่มี ให้ลองหาที่ C:\Program Files\Tesseract-OCR\tesseract.exe เป็นหลัก
tesseract_path = os.getenv("TESSERACT_CMD_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

if tesseract_path and os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    print(f"[Warning] ไม่พบโปรแกรม Tesseract ในเครื่องที่พาท: {tesseract_path} (กรุณาตรวจสอบการติดตั้ง Tesseract-OCR)")

class DocumentProcessor:
    """
    คลาสจัดการเอกสาร PDF พร้อมระบบ Fallback เป็น OCR (วิเคราะห์แสกนข้อความรูปภาพ)
    เมื่อเจอไฟล์ PDF สแกน (รูปแบบรูปหน้ากระดาษ)
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def _ocr_pdf_with_pymupdf(self, file_path: str) -> List[Document]:
        """
        โหมดปฏิบัติการ OCR: หั่น PDF เป็นภาพทีละหน้าแล้วสั่ง Tesseract อ่านข้อความไทย+อังกฤษ
        """
        print(f"[OCR Mode] กำลังเริ่มถอดรหัสรูปภาพในเอกสาร: {os.path.basename(file_path)}...")
        doc = fitz.open(file_path)
        documents = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # ปรับเพิ่ม DPI (ความคมชัด) เล็กน้อยให้ OCR อ่านได้แม่นยำขึ้น
            pix = page.get_pixmap(dpi=150)
            
            # แปลงภาพของ PyMuPDF เป็นรูปแบบ Pillow Image ที่ pytesseract เข้าใจ
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            try:
                # รัน OCR ด้วยคำสั่งดึงภาษาไทย (tha) และอังกฤษ (eng)
                text = pytesseract.image_to_string(img, lang='tha+eng')
                # กรองคำผิดปกติจากการแสกนหน้าเปล่าทิ้งไป
                text = text.strip()
                
                # จำลองโครงสร้างให้เหมือนการโหลด LangChain ปกติ
                doc_metadata = {"source": file_path, "page": page_num}
                documents.append(Document(page_content=text, metadata=doc_metadata))
                
            except Exception as e:
                print(f"[Error] พบข้อผิดพลาดขณะทำ OCR หน้าที่ {page_num + 1}: {e}")
                
        doc.close()
        return documents

    def load_pdf(self, file_path: str) -> List[Document]:
        """
        โหลดไฟล์ PDF ชิ้นเดียว (ใช้ PyPDFLoader ปกติ ถ้าเป็นหน้าเปล่า/แสกน จะสลับไปใช้ OCR อัตโนมัติ)
        """
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"ไม่พบไฟล์ PDF ที่ระบุ: {file_path}")
             
        # ขั้นที่ 1: พยายามอ่านแบบปกติอย่างรวดเร็วก่อน
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # ตรวจสอบว่าหลังจากอ่านทั้งหมดแล้ว แทบไม่มีข้อความเลย (แปลว่าเป็นไฟล์รูป/แสกน)
        total_text_length = sum(len(d.page_content.strip()) for d in documents)
        
        # ถ้ายาวไม่ถึง 50 ตัวอักษรทั้งเล่ม สันนิษฐานเอาไว้ก่อนว่าถูกเซฟมาแบบฝังรูป
        if total_text_length < 50:
            print(f"[Warning] ตรวจพบเอกสารแสกน! ระบบปกติดึงข้อความไม่ได้ จะทำการสลับเข้าโหมด OCR")
            # ฝากภาระให้ Tesseract ช่วยอ่าน
            documents = self._ocr_pdf_with_pymupdf(file_path)
            
        return documents

    def process_document(self, file_path: str) -> List[Document]:
        """
        โหลดและหั่น (Split) ทันที พร้อมเก็บ Metadata ของหน้า
        """
        print(f"[Log] กำลังอ่านไฟล์: {file_path}")
        documents = self.load_pdf(file_path)
        
        valid_docs = [doc for doc in documents if doc.page_content.strip()]
        
        if not valid_docs:
             print(f"[Failed] ไม่สามารถหั่นข้อความได้ เนื่องจากเอกสารไม่มีตัวหนังสือที่อ่านออกเลย")
             return []
             
        print(f"[Log] อ่านเสร็จ จำนวนทั้งหมด {len(documents)} หน้า กำลังหั่นข้อความ...")
        chunks = self.text_splitter.split_documents(valid_docs)
        
        print(f"[Log] หั่นข้อความสำเร็จ ได้จำนวนทั้งหมด {len(chunks)} Chunks")
        return chunks
        
    def process_directory(self, folder_path: str) -> List[Document]:
        """
        ฟังก์ชันสำหรับกวาดโหลดไฟล์ PDF ทั้งหมดในโฟลเดอร์
        """
        all_chunks = []
        if not os.path.exists(folder_path):
             os.makedirs(folder_path)
             print(f"[Log] ไม่พบโฟลเดอร์ {folder_path} จึงสร้างโฟลเดอร์รอกดออมข้อมูลไฟล์ให้")
             return all_chunks

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(".pdf"):
                full_path = os.path.join(folder_path, filename)
                chunks = self.process_document(full_path)
                all_chunks.extend(chunks)
                
        return all_chunks

if __name__ == "__main__":
    print("ทดสอบระบบ Document Loader (พร้อมฟีเจอร์ช่วยอ่านภาษาไทยแบบ OCR)")
    processor = DocumentProcessor()
    
    sample_dir = "data"
    chunks = processor.process_directory(sample_dir)
    print(f"รวม Chunk ทั้งหมดในระบบ: {len(chunks)}")
    if chunks:
         print(f"ตัวอย่างประโยคชิ้นแรก: '{chunks[0].page_content[:150]}...' [หน้า {chunks[0].metadata.get('page')}]")
