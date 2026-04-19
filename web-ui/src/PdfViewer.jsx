import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { 
  X, 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  Download,
  Loader2,
  FileText
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// เผื่อคนรันใน local แล้วหา worker ไม่เจอ ให้ดึงจาก CDN ครับ
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const PdfViewer = ({ isOpen, onClose, fileUrl, initialPage = 1, fileName }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(1.0);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    if (initialPage > numPages) setPageNumber(1);
    else setPageNumber(initialPage);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1rem',
          backgroundColor: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(4px)'
        }}
      >
        <motion.div 
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="glass w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden"
          style={{
            backgroundColor: 'var(--glass-bg)',
            border: '1px solid var(--glass-border)',
            borderRadius: '1.5rem',
            width: '100%',
            maxWidth: '1200px',
            height: '90vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}
        >
          {/* Header */}
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--glass-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255,255,255,0.03)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ color: 'var(--accent-primary)' }}><FileText size={20} /></div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{fileName || 'Document Viewer'}</h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Page {pageNumber} of {numPages || '--'}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div className="flex items-center glass p-1 rounded-lg" style={{ display: 'flex', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '0.75rem', padding: '0.25rem' }}>
                <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={{ padding: '0.5rem', border: 'none', background: 'none', color: 'white', cursor: 'pointer' }}><ZoomOut size={18} /></button>
                <span style={{ fontSize: '0.8rem', padding: '0 0.5rem', minWidth: '3.5rem', textAlign: 'center' }}>{Math.round(scale * 100)}%</span>
                <button onClick={() => setScale(s => Math.min(2.0, s + 0.1))} style={{ padding: '0.5rem', border: 'none', background: 'none', color: 'white', cursor: 'pointer' }}><ZoomIn size={18} /></button>
              </div>
              
              <div style={{ width: '1px', height: '20px', backgroundColor: 'var(--glass-border)', margin: '0 0.5rem' }} />

              <button 
                onClick={onClose}
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  color: '#f87171',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.4)'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.2)'}
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* PDF Content Area */}
          <div style={{ 
            flex: 1, 
            overflow: 'auto', 
            padding: '2rem', 
            display: 'flex', 
            justifyContent: 'center', 
            backgroundColor: 'rgba(0,0,0,0.15)',
            scrollbarWidth: 'thin',
            scrollbarColor: 'var(--glass-border) transparent'
          }}>
            <Document
              file={fileUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', marginTop: '5rem' }}>
                  <Loader2 size={40} className="spin" color="var(--accent-primary)" />
                  <p style={{ color: 'var(--text-secondary)' }}>กำลังโหลดเอกสาร...</p>
                </div>
              }
              error={
                <div style={{ textAlign: 'center', marginTop: '5rem' }}>
                  <X size={48} color="#f87171" style={{ margin: '0 auto 1rem' }} />
                  <p>ไม่สามารถโหลดไฟล์ได้ (File not found)</p>
                </div>
              }
            >
              <Page 
                pageNumber={pageNumber} 
                scale={scale} 
                renderTextLayer={true}
                renderAnnotationLayer={true}
                className="pdf-page-shadow"
              />
            </Document>
          </div>

          {/* Navigation Footer */}
          <div style={{
            padding: '1rem',
            borderTop: '1px solid var(--glass-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255,255,255,0.03)',
            gap: '1.5rem'
          }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => setPageNumber(p => Math.max(1, p - 1))}
              disabled={pageNumber <= 1}
              style={{ borderRadius: '0.75rem' }}
            >
              <ChevronLeft size={20} /> Previous
            </button>
            
            <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
              {pageNumber} / {numPages || '--'}
            </div>

            <button 
              className="btn btn-secondary" 
              onClick={() => setPageNumber(p => Math.min(numPages, p + 1))}
              disabled={pageNumber >= numPages}
              style={{ borderRadius: '0.75rem' }}
            >
              Next <ChevronRight size={20} />
            </button>
          </div>
        </motion.div>
      </motion.div>
      
      <style dangerouslySetInnerHTML={{ __html: `
        .pdf-page-shadow canvas {
          box-shadow: 0 10px 30px rgba(0,0,0,0.4);
          border-radius: 4px;
        }
        /* บังคับให้ข้อความใน PDF เป็นสีดำเพื่อให้อ่านได้บนพื้นขาว */
        .react-pdf__Page__textContent {
          color: black !important;
          mix-blend-mode: multiply;
        }
        /* Custom scrollbar for PDF area */
        .pdf-container::-webkit-scrollbar { width: 8px; }
        .pdf-container::-webkit-scrollbar-thumb { background: var(--glass-border); border-radius: 10px; }
      `}} />
    </AnimatePresence>
  );
};

export default PdfViewer;
