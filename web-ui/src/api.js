import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const uploadFiles = async (files) => {
  const formData = new FormData();
  Array.from(files).forEach((file) => {
    formData.append('files', file);
  });
  return api.post('/api/upload-indexing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const chat = async (message) => {
  return api.post('/api/chat', { message });
};

export const fetchGraphData = async () => {
  return api.get('/api/graph-data');
};

export default api;
