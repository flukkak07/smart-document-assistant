# ใช้ Python 3.11 แบบ slim เพื่อให้ขนาด Image เล็กและโหลดเร็ว
FROM python:3.11-slim

# ตั้งค่า Working Directory
WORKDIR /app

# ติดตั้ง System Dependencies ที่จำเป็น
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# คัดลอกไฟล์ requirements.txt และติดตั้ง Python Library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมดเข้าเครื่อง
COPY . .

# สร้างโฟลเดอร์สำหรับอัปโหลดไฟล์ (ถ้ายังไม่มี)
RUN mkdir -p uploads

# เปิด Port ตามที่แอปใช้งาน
EXPOSE 8000

# คำสั่งสำหรับรันแอปพลิเคชัน
# ใช้ uvicorn รัน api_server.py
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
