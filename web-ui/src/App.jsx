import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  FileText, 
  Upload, 
  Brain, 
  MessageSquare, 
  Network, 
  RefreshCw, 
  Trash2, 
  Info,
  ChevronRight,
  Loader2,
  Terminal,
  ExternalLink,
  ShieldCheck,
  Target,
  Zap,
  Search,
  X as CloseIcon,
  Menu,
  Shield,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ForceGraph2D from 'react-force-graph-2d';
import axios from 'axios';
import { uploadFiles, fetchGraphData } from './api';
import PdfViewer from './PdfViewer';
import API_URL from './config';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [indexed, setIndexed] = useState(false);
  const [logs, setLogs] = useState([]);
  const [isEvaluating, setIsEvaluating] = useState(null); // Message index currently being evaluated
  
  // PDF Viewer State
  const [viewerConfig, setViewerConfig] = useState({
    isOpen: false,
    fileUrl: '',
    page: 1,
    fileName: ''
  });

  // Advanced Graph State
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetails, setNodeDetails] = useState(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [hiddenCategories, setHiddenCategories] = useState(new Set());
  const [contextMenu, setContextMenu] = useState(null);
  
  const chatEndRef = useRef(null);
  const logEndRef = useRef(null);
  const graphRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Polling for indexing status
  useEffect(() => {
    let interval;
    if (isUploading) {
      interval = setInterval(async () => {
        try {
          const resp = await axios.get(`${API_URL}/api/indexing-status`);
          setLogs(resp.data.logs);
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isUploading]);

  useEffect(() => {
    if (activeTab === 'graph') {
      fetchGraphData().then(resp => setGraphData(resp.data)).catch(err => console.error(err));
    }
  }, [activeTab]);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    setLogs(["[System] กำลังเตรียมการอัปโหลด..."]);
    try {
      await axios.get(`${API_URL}/api/clear-logs`);
      await uploadFiles(files);
      setIndexed(true);
      const gd = await fetchGraphData();
      setGraphData(gd.data);
    } catch (err) {
      console.error(err);
      setLogs(prev => [...prev, "❌ Error: ไม่สามารถอัปโหลดข้อมูลได้"]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleChat = async () => {
    if (!input.trim() || isChatting) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsChatting(true);
    setMessages(prev => [...prev, { role: 'ai', content: '', metadata: null, evaluation: null }]);

    const currentQuestion = input;

    try {
      const response = await fetch(`${API_URL}/api/chat-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentQuestion })
      });

      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') { finished = true; break; }
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'status') {
                setLogs(prev => [...prev, `[AI Status] ${data.value}`]);
              } else if (data.type === 'metadata') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  newMsgs[lastIdx] = { 
                    ...newMsgs[lastIdx], 
                    metadata: { 
                      route: data.route, 
                      sources: data.sources || [], 
                      contexts: data.contexts || [],
                      question: currentQuestion
                    } 
                  };
                  return newMsgs;
                });
              } else if (data.type === 'content') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: newMsgs[lastIdx].content + data.value };
                  return newMsgs;
                });
              }
            } catch (e) { }
          }
        }
      }
    } catch (err) { } finally { setIsChatting(false); }
  };

  const handleVerify = async (msgIdx) => {
    const msg = messages[msgIdx];
    if (!msg.metadata?.contexts || isEvaluating !== null) return;
    
    setIsEvaluating(msgIdx);
    try {
      const resp = await axios.post(`${API_URL}/api/evaluate`, {
        question: msg.metadata.question || "",
        answer: msg.content,
        contexts: msg.metadata.contexts
      });
      
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[msgIdx] = { ...newMsgs[msgIdx], evaluation: resp.data };
        return newMsgs;
      });
    } catch (err) {
      console.error("Evaluation failed", err);
    } finally {
      setIsEvaluating(null);
    }
  };

  const expandNode = async (node) => {
    try {
      const resp = await axios.get(`${API_URL}/api/graph/neighbors/${node.id}`);
      const { nodes: newNodes, links: newLinks } = resp.data;
      setGraphData(prev => {
        const existingNodeIds = new Set(prev.nodes.map(n => n.id));
        const filteredNewNodes = newNodes.filter(n => !existingNodeIds.has(n.id));
        const existingLinkIds = new Set(prev.links.map(l => {
          const s = typeof l.source === 'object' ? l.source.id : l.source;
          const t = typeof l.target === 'object' ? l.target.id : l.target;
          return `${s}-${t}`;
        }));
        const filteredNewLinks = newLinks.filter(l => !existingLinkIds.has(`${l.source}-${l.target}`));
        return { nodes: [...prev.nodes, ...filteredNewNodes], links: [...prev.links, ...filteredNewLinks] };
      });
    } catch (err) { }
  };

  const fetchNodeDetails = async (node) => {
    setSelectedNode(node);
    setNodeDetails(null);
    setIsLoadingDetails(true);
    try {
      const resp = await axios.get(`${API_URL}/api/graph/node-details/${node.id}`);
      setNodeDetails(resp.data);
    } catch (err) { } finally { setIsLoadingDetails(false); }
  };

  const handleNodeSearch = (query) => {
    setSearchQuery(query);
    if (!query) return;
    const found = graphData.nodes.find(n => (n.properties?.id || n.id).toLowerCase().includes(query.toLowerCase()));
    if (found && graphRef.current) {
      graphRef.current.centerAt(found.x, found.y, 800);
      graphRef.current.zoom(2.2, 800);
    }
  };

  const toggleCategory = (label) => {
    setHiddenCategories(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const categories = React.useMemo(() => {
    const cats = new Set();
    graphData.nodes.forEach(n => cats.add(n.label?.toUpperCase() || 'ENTITY'));
    const palette = { 'ACTION': '#2dd4bf', 'BENEFIT': '#6366f1', 'DISEASE': '#f59e0b', 'OBJECT': '#a78bfa', 'SUBJECT': '#3b82f6', 'SUBSTANCE': '#ec4899' };
    return Array.from(cats).map(label => ({
      label,
      color: palette[label] || `hsl(${Math.abs(label.length * 137.5) % 360}, 75%, 60%)`
    })).sort((a,b) => a.label.localeCompare(b.label));
  }, [graphData]);

  const filteredGraphData = React.useMemo(() => {
    const nodes = graphData.nodes.filter(n => !hiddenCategories.has(n.label?.toUpperCase() || 'ENTITY'));
    const activeIds = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l => {
      const sId = typeof l.source === 'object' ? l.source.id : l.source;
      const tId = typeof l.target === 'object' ? l.target.id : l.target;
      return activeIds.has(sId) && activeIds.has(tId);
    });
    return { nodes, links };
  }, [graphData, hiddenCategories]);

  const askAIAboutNode = (node) => {
    const name = node.properties?.id || node.id;
    setInput(`เล่ารายละเอียดเกี่ยวกับ "${name}" ในเอกสารชุดนี้ให้ฟังหน่อย`);
    setActiveTab('chat');
    setContextMenu(null);
  };

  const openPdf = (file, page) => {
    setViewerConfig({ isOpen: true, fileUrl: `${API_URL}/pdf-files/${file}`, page, fileName: file });
  };

  const ConfidenceBar = ({ label, score, color }) => (
    <div style={{ marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginBottom: '0.2rem' }}>
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span>{Math.round(score * 100)}%</span>
      </div>
      <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${score * 100}%` }} style={{ height: '100%', backgroundColor: color }} />
      </div>
    </div>
  );

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
          <div style={{ backgroundColor: 'var(--accent-primary)', padding: '0.5rem', borderRadius: '0.75rem' }}><Brain size={24} color="white" /></div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'Outfit' }}>Smart Documents</h1>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.25rem' }}>
          <nav>
            <button className={`btn ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`} style={{ width: '100%', marginBottom: '0.75rem', justifyContent: 'flex-start' }} onClick={() => setActiveTab('chat')}><MessageSquare size={18} /> Smart Assistant</button>
            <button className={`btn ${activeTab === 'graph' ? 'btn-primary' : 'btn-secondary'}`} style={{ width: '100%', justifyContent: 'flex-start' }} onClick={() => setActiveTab('graph')}><Network size={18} /> Relationship Graph</button>
          </nav>
          
          <div style={{ marginTop: '2rem' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '1rem', letterSpacing: '0.05em' }}>Knowledge Base</label>
            <div className="glass" style={{ padding: '1.5rem', border: '2px dashed var(--glass-border)', textAlign: 'center', cursor: 'pointer' }} onClick={() => document.getElementById('fileInput').click()}>
              <Upload size={32} style={{ margin: '0 auto 0.75rem', color: 'var(--accent-primary)' }} /><p style={{ fontSize: '0.875rem' }}>Upload PDF Here</p>
              <input id="fileInput" type="file" multiple accept=".pdf" hidden onChange={(e) => setFiles(e.target.files)} />
            </div>
            {files.length > 0 && (
              <div style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                {Array.from(files).map((f, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', marginBottom: '0.25rem', color: 'var(--text-secondary)' }}><FileText size={12} /> {f.name}</div>
                ))}
              </div>
            )}
            <button className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} onClick={handleUpload} disabled={files.length === 0 || isUploading}>
              {isUploading ? <Loader2 size={18} className="spin" /> : <RefreshCw size={18} />} {isUploading ? 'Processing...' : 'Build Knowledge Base'}
            </button>
          </div>

          <div style={{ marginTop: '2rem' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Terminal size={14} color="var(--text-secondary)" />
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Activity Monitor</span>
             </div>
             <div className="glass" style={{ height: '180px', overflowY: 'auto', padding: '0.75rem', fontSize: '0.7rem', fontFamily: 'monospace', backgroundColor: 'rgba(0,0,0,0.3)' }}>
                {logs.length === 0 ? <div style={{ color: 'rgba(255,255,255,0.2)' }}>standby...</div> : logs.map((log, i) => <div key={i} style={{ marginBottom: '0.25rem' }}>{log}</div>)}
                <div ref={logEndRef} />
             </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activeTab === 'chat' ? (
          <>
            <div className="chat-container">
              <AnimatePresence>
                {messages.length === 0 ? (
                  <div style={{ padding: '3.5rem', maxWidth: '650px', margin: 'auto', textAlign: 'center' }}>
                    <Brain size={80} style={{ margin: '0 auto 2rem', color: 'var(--accent-primary)', filter: 'drop-shadow(0 0 15px var(--accent-primary))' }} />
                    <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1rem', fontFamily: 'Outfit' }}>Smart Document Assistant</h2>
                    <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>ระบบวิเคราะห์เอกสารอัจฉริยะ พร้อมการเชื่อมโยงข้อมูลแบบ Knowledge Graph ระดับสากล</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`chat-bubble ${msg.role === 'ai' ? 'ai glass' : 'user glass'}`}>
                       <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.6rem', opacity: 0.7 }}>{msg.role === 'ai' ? 'AI Assistant' : 'You'}</div>
                       <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content || (isChatting && idx === messages.length - 1 ? <Loader2 size={16} className="spin" /> : '')}</div>
                       
                       {msg.role === 'ai' && (
                         <div style={{ marginTop: '1rem', borderTop: '1px solid var(--glass-border)', paddingTop: '0.75rem' }}>
                            {msg.metadata?.sources?.length > 0 && (
                              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                                {msg.metadata.sources.map((src, si) => (
                                  <button key={si} className="btn-secondary" style={{ fontSize: '0.65rem', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }} onClick={() => openPdf(src.file, src.page)}><FileText size={10} /> {src.file} (P.{src.page})</button>
                                ))}
                              </div>
                            )}

                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              {!msg.evaluation ? (
                                <button className="btn-secondary" style={{ fontSize: '0.65rem', padding: '6px 12px', border: '1px solid var(--accent-primary)' }} onClick={() => handleVerify(idx)} disabled={isEvaluating !== null}>
                                  {isEvaluating === idx ? <Loader2 size={14} className="spin" /> : <ShieldCheck size={14} />} 
                                  {isEvaluating === idx ? 'Verifying...' : 'Verify Response Accuracy'}
                                </button>
                              ) : (
                                <div style={{ width: '100%' }}>
                                   <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                      {msg.evaluation.faithfulness > 0.7 ? <CheckCircle2 size={16} color="#2dd4bf" /> : <AlertCircle size={16} color="#f59e0b" />}
                                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: msg.evaluation.faithfulness > 0.7 ? '#2dd4bf' : '#f59e0b' }}>
                                        {msg.evaluation.faithfulness > 0.7 ? 'Verified - Document Grounded' : 'Warning - Check Sources'}
                                      </span>
                                   </div>
                                   <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                      <ConfidenceBar label="FAITHFULNESS" score={msg.evaluation.faithfulness} color="#2dd4bf" />
                                      <ConfidenceBar label="RELEVANCY" score={msg.evaluation.answer_relevancy} color="#6366f1" />
                                   </div>
                                </div>
                              )}
                            </div>
                         </div>
                       )}
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
              <div ref={chatEndRef} />
            </div>
            <div className="input-area">
              <div className="glass input-wrapper" style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem' }}>
                <textarea placeholder="Ask something about your docs..." rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChat(); } }} />
                <button className="btn btn-primary" style={{ width: '48px', height: '48px', padding: 0, flexShrink: 0 }} onClick={handleChat} disabled={isChatting || !input.trim()}>{isChatting ? <Loader2 size={22} className="spin" /> : <Send size={22} />}</button>
              </div>
            </div>
          </>
        ) : (
          <div className="graph-container" onClick={() => setContextMenu(null)}>
            <div className="graph-controls">
                <div className="graph-search-wrapper"><Search size={18} color="var(--text-secondary)" /><input className="graph-search-input" placeholder="Search..." value={searchQuery} onChange={(e) => handleNodeSearch(e.target.value)} /></div>
                <div className="graph-legend">
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '1rem', color: 'var(--text-secondary)' }}>Categories ({categories.length})</div>
                  {categories.map(cat => (
                    <div key={cat.label} className={`legend-item ${hiddenCategories.has(cat.label) ? 'hidden' : ''}`} onClick={(e) => { e.stopPropagation(); toggleCategory(cat.label); }}>
                      <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: cat.color }} />
                      <span style={{ fontSize: '0.75rem' }}>{cat.label}</span>
                    </div>
                  ))}
                </div>
            </div>

            <AnimatePresence>
              {selectedNode && (
                <motion.div initial={{ x: 300 }} animate={{ x: 0 }} exit={{ x: 300 }} className="node-details-panel shadow-2xl">
                  <div className="panel-header">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--accent-primary)', letterSpacing: '0.1em' }}>{selectedNode.label?.toUpperCase()}</span>
                      <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }} className="hover:text-white transition-colors"><CloseIcon size={20} /></button>
                    </div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>{selectedNode.properties?.id || selectedNode.id}</h2>
                  </div>

                  <div className="panel-content">
                    {isLoadingDetails ? (
                      <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><Loader2 className="spin" size={32} color="var(--accent-primary)" /></div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', borderLeft: '3px solid var(--accent-primary)', paddingLeft: '0.75rem' }}>
                          พบข้อมูลอ้างอิง {nodeDetails?.sources?.length || 0} ส่วนจากเอกสาร
                        </div>
                        {nodeDetails?.sources?.map((s, i) => (
                          <div key={i} className="source-chunk-card">
                            <p style={{ marginBottom: '0.75rem' }}>"{s.content}"</p>
                            <div style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <FileText size={12} /> {s.metadata.source} (Page {s.metadata.page})
                            </div>
                          </div>
                        ))}
                        <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => askAIAboutNode(selectedNode)}>
                          <Brain size={18} /> Ask AI Knowledge
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {contextMenu && (
              <div className="context-menu" style={{ top: contextMenu.y, left: contextMenu.x }}>
                <div className="context-menu-item" onClick={() => { fetchNodeDetails(contextMenu.node); setContextMenu(null); }}><Info size={14} /> Detail View</div>
                <div className="context-menu-item" onClick={() => { expandNode(contextMenu.node); setContextMenu(null); }}><RefreshCw size={14} /> Expand Neighbors</div>
                <div className="context-menu-item" onClick={() => askAIAboutNode(contextMenu.node)}><Brain size={14} /> Ask AI Knowledge</div>
              </div>
            )}

            <ForceGraph2D
              ref={graphRef}
              graphData={filteredGraphData}
              backgroundColor="#020617"
              nodeLabel={n => `[${n.label}] ${n.properties?.id || n.id}`}
              nodeColor={(node) => {
                const label = node.label?.toUpperCase() || 'ENTITY';
                const cat = categories.find(c => c.label === label);
                return cat ? cat.color : '#94a3b8';
              }}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const label = node.properties?.id || node.id; const fontSize = 14 / globalScale; ctx.font = `${fontSize}px Sarabun`;
                const textWidth = ctx.measureText(label).width; const bck = [textWidth, fontSize].map(n => n + fontSize * 0.2);
                ctx.fillStyle = selectedNode?.id === node.id ? '#0d9488' : 'rgba(15, 23, 42, 0.8)';
                ctx.fillRect(node.x - bck[0] / 2, node.y + 10, bck[0], bck[1]);
                ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#fff'; ctx.fillText(label, node.x, node.y + 10 + fontSize / 2);
                ctx.beginPath(); ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
                const nodeLabel = node.label?.toUpperCase() || 'ENTITY';
                const cat = categories.find(c => c.label === nodeLabel);
                ctx.fillStyle = cat ? cat.color : '#94a3b8';
                ctx.fill();
                if (selectedNode?.id === node.id) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 2 / globalScale; ctx.stroke(); }
              }}
              linkDirectionalParticles={4}
              linkWidth={2}
              linkColor={() => 'rgba(255,255,255,0.1)'}
              onNodeClick={fetchNodeDetails}
              onNodeRightClick={(node, event) => {
                event.preventDefault();
                setContextMenu({ x: event.clientX, y: event.clientY, node });
              }}
              linkCanvasObjectMode={() => 'after'}
              linkCanvasObject={(link, ctx, globalScale) => {
                if (typeof link.source !== 'object' || typeof link.target !== 'object') return;
                const fontSize = 4 / globalScale; ctx.font = `${fontSize}px Sarabun`;
                const pos = { x: link.source.x + (link.target.x - link.source.x) / 2, y: link.source.y + (link.target.y - link.source.y) / 2 };
                ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.textAlign = 'center'; ctx.fillText(link.type || '', pos.x, pos.y);
              }}
            />
          </div>
        )}
      </main>

      <PdfViewer isOpen={viewerConfig.isOpen} fileUrl={viewerConfig.fileUrl} initialPage={viewerConfig.page} fileName={viewerConfig.fileName} onClose={() => setViewerConfig(p => ({ ...p, isOpen: false }))} />

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
        .chat-container::-webkit-scrollbar { width: 6px; }
        .chat-container::-webkit-scrollbar-thumb { background: var(--glass-border); border-radius: 10px; }
      `}} />
    </div>
  );
}

export default App;
