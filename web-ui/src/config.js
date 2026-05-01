// ตั้งค่า API URL สำหรับ Frontend
// ในช่วงพัฒนาจะใช้ localhost แต่เมื่อ Deploy จะใช้ค่าจาก Environment Variable หรือ URL ของ Railway
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default API_URL;
