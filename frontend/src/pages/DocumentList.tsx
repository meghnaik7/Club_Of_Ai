import React, { useState, useEffect } from 'react';
import {
  FileText, Search, Upload, Trash2, Sparkles, BookOpen, Send, Loader2,
  History, ShieldCheck, CheckCircle2, Lock, Mic, Square, Volume2
} from 'lucide-react';
import VoiceService from '../services/voice.service';
import VoiceAssistant from '../components/voice/VoiceAssistant';
import DashboardLayout from '../components/DashboardLayout';
import DocumentsService from '../services/documents.service';
import type { DocumentItem, RAGHistoryItem } from '../services/documents.service';
import { useAuth } from '../context/AuthContext';

export default function DocumentList() {
  const [activeTab, setActiveTab] = useState<'rag' | 'files'>('rag');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [history, setHistory] = useState<RAGHistoryItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // RAG Query state
  const [query, setQuery] = useState('');
  const [asking, setAsking] = useState(false);

  // Voice Assistant Modal
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  // Quick Mic Recording (STT direct to RAG Query)
  const [isQuickRecording, setIsQuickRecording] = useState(false);
  const quickMediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const quickAudioChunksRef = React.useRef<Blob[]>([]);
  const quickStreamRef = React.useRef<MediaStream | null>(null);

  // Audio TTS playback state for past answers
  const [playingAnswerId, setPlayingAnswerId] = useState<number | null>(null);
  const [loadingTTSId, setLoadingTTSId] = useState<number | null>(null);
  const activeAudioRef = React.useRef<HTMLAudioElement | null>(null);

  // Upload modal
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState('POST_MORTEM');
  const [uploadError, setUploadError] = useState('');

  const { isAdmin } = useAuth();
  const canUpload = Boolean(isAdmin);

  // Search
  const [searchFilter, setSearchFilter] = useState('');

  // Fetch past RAG questions and answers once user opens the page
  const fetchRAGHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await DocumentsService.getRAGHistory();
      setHistory(data.items || []);
    } catch (err) {
      console.error('Failed to load RAG history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const data = await DocumentsService.listDocuments({ search: searchFilter });
      setDocuments(data.items || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchRAGHistory();
    fetchDocuments();
  }, []);

  // Quick Mic Recording (STT)
  const startQuickRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      quickStreamRef.current = stream;
      quickAudioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : '';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      quickMediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          quickAudioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        if (quickStreamRef.current) {
          quickStreamRef.current.getTracks().forEach((track) => track.stop());
          quickStreamRef.current = null;
        }

        const audioBlob = new Blob(quickAudioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });

        if (audioBlob.size > 100) {
          setAsking(true);
          try {
            const transcription = await VoiceService.transcribe(audioBlob, { language: 'auto' });
            if (transcription.transcript?.trim()) {
              setQuery(transcription.transcript);
              await DocumentsService.queryRAG({ query: transcription.transcript });
              setQuery('');
              fetchRAGHistory();
            }
          } catch (err: any) {
            console.error('Quick voice transcription failed:', err);
            alert('Voice transcription failed. Please try again or type your question.');
          } finally {
            setAsking(false);
          }
        }
        setIsQuickRecording(false);
      };

      recorder.start(100);
      setIsQuickRecording(true);
    } catch (err) {
      console.error('Microphone error:', err);
      alert('Could not access microphone. Please check permissions in your browser.');
      setIsQuickRecording(false);
    }
  };

  const stopQuickRecording = () => {
    if (quickMediaRecorderRef.current && quickMediaRecorderRef.current.state === 'recording') {
      quickMediaRecorderRef.current.stop();
    }
    setIsQuickRecording(false);
  };

  // Answer Text-to-Speech Playback
  const handlePlayAnswerAudio = async (item: RAGHistoryItem) => {
    if (playingAnswerId === item.id) {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }
      setPlayingAnswerId(null);
      return;
    }

    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
      setPlayingAnswerId(null);
    }

    setLoadingTTSId(item.id);
    try {
      const textToSpeak = item.answer.length > 300 ? item.answer.slice(0, 300) + '...' : item.answer;
      const synth = await VoiceService.synthesize({
        text: textToSpeak,
        language: 'en-IN',
      });

      const audioUrl = `data:${synth.content_type || 'audio/wav'};base64,${synth.audio_base64}`;
      const audio = new Audio(audioUrl);
      activeAudioRef.current = audio;
      setPlayingAnswerId(item.id);

      audio.onended = () => {
        setPlayingAnswerId(null);
        activeAudioRef.current = null;
      };
      audio.onerror = () => {
        setPlayingAnswerId(null);
        activeAudioRef.current = null;
      };

      await audio.play();
    } catch (err) {
      console.error('Failed to synthesize speech for answer:', err);
    } finally {
      setLoadingTTSId(null);
    }
  };

  const handleAskRAG = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || asking) return;

    const promptText = query.trim();
    setAsking(true);
    try {
      await DocumentsService.queryRAG({ query: promptText });
      setQuery('');
      // Refresh history to include newly saved turn
      fetchRAGHistory();
    } catch (err: any) {
      console.error('Error querying RAG:', err);
    } finally {
      setAsking(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Clear all past asked questions and answers?')) return;
    try {
      await DocumentsService.clearRAGHistory();
      setHistory([]);
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canUpload) {
      setUploadError('Permission denied: Only System Admin can upload documents for RAG.');
      return;
    }
    if (!uploadFile) return;

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('category', uploadCategory);

    setIsUploading(true);
    setUploadError('');
    try {
      await DocumentsService.uploadDocument(formData);
      setUploadFile(null);
      fetchDocuments();
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this document and its embeddings?')) return;
    try {
      await DocumentsService.deleteDocument(id);
      fetchDocuments();
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  return (
    <DashboardLayout title="Documents & Club Brain">
      <div className="space-y-6">
        {/* Header Banner */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/80 p-6 rounded-2xl border border-slate-800 shadow-xl backdrop-blur-sm">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
                Retrieval-Augmented Generation (RAG)
              </span>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-indigo-400" />
              Club Brain & Knowledge Base
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Ask questions about past events, budgets, venue policies, and post-mortems with verified citations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsVoiceModalOpen(true)}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-violet-600 hover:bg-violet-500 text-white flex items-center gap-2 shadow-lg shadow-violet-600/25 transition-all border border-violet-400/30 shrink-0 cursor-pointer"
              title="Open Multilingual Voice Assistant"
            >
              <Mic className="w-4 h-4 text-violet-200" />
              <span>Voice RAG Assistant</span>
            </button>
            <div className="flex items-center gap-2 bg-slate-800/80 p-1.5 rounded-xl border border-slate-700/50">
            <button
              onClick={() => setActiveTab('rag')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150 flex items-center gap-2 ${
                activeTab === 'rag'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              RAG Q&A
              {history.length > 0 && (
                <span className="text-[11px] bg-indigo-900/80 text-indigo-200 px-1.5 py-0.2 rounded-full">
                  {history.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('files')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-150 flex items-center gap-2 ${
                activeTab === 'files'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="w-4 h-4" />
              Documents ({documents.length})
            </button>
          </div>
          </div>
        </div>

        {/* TAB 1: RAG Q&A WITH PAST QUESTIONS & ANSWERS */}
        {activeTab === 'rag' && (
          <div className="space-y-6">
            {/* Input Question Box */}
            <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl space-y-4">
              <form onSubmit={handleAskRAG} className="space-y-3">
                <label className="text-sm font-semibold text-slate-200 flex items-center justify-between">
                  <span>Ask Club Brain a Question</span>
                  <span className="text-xs text-slate-500 font-normal flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    Ground truth source citations enforced
                  </span>
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g. What was our meal reimbursement limit? What went wrong at the hackathon?"
                      className="w-full bg-slate-950 border border-slate-700/80 focus:border-indigo-500 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
                    />
                    <button
                      type="button"
                      onClick={isQuickRecording ? stopQuickRecording : startQuickRecording}
                      disabled={asking}
                      className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-all flex items-center justify-center cursor-pointer ${
                        isQuickRecording
                          ? 'bg-rose-600 text-white animate-pulse shadow-md shadow-rose-600/40'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                      title={isQuickRecording ? 'Click to stop & ask RAG' : 'Speak your question (Voice STT)'}
                    >
                      {isQuickRecording ? <Square className="w-4 h-4 fill-white" /> : <Mic className="w-4 h-4 text-violet-400" />}
                    </button>
                  </div>
                  <button
                    type="submit"
                    disabled={asking || !query.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold px-6 py-3 rounded-xl transition-all flex items-center gap-2 shrink-0 shadow-lg shadow-indigo-600/20"
                  >
                    {asking ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Ask RAG
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Past Asked Questions & Answers History Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <History className="w-4 h-4 text-indigo-400" />
                  Previous Past Asked Questions & Answers
                  <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                    {history.length} past conversations
                  </span>
                </h3>

                {history.length > 0 && (
                  <button
                    onClick={handleClearHistory}
                    className="text-xs text-slate-400 hover:text-red-400 flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-slate-800/80 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Clear History
                  </button>
                )}
              </div>

              {loadingHistory ? (
                <div className="bg-slate-900/50 border border-slate-800/80 p-8 rounded-2xl flex items-center justify-center gap-2 text-slate-400">
                  <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                  Loading conversation history...
                </div>
              ) : history.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-800/60 p-8 rounded-2xl text-center space-y-2">
                  <p className="text-sm font-medium text-slate-300">No previous questions asked yet.</p>
                  <p className="text-xs text-slate-500">
                    Ask your first question above! All your questions, answers, and sources will be remembered here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {history.map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl shadow-md space-y-3 transition-all hover:border-slate-700/80"
                    >
                      {/* Question */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-2.5">
                          <span className="w-6 h-6 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-bold flex items-center justify-center shrink-0">
                            Q
                          </span>
                          <h4 className="text-sm font-bold text-white leading-relaxed">
                            {item.question}
                          </h4>
                        </div>
                        {item.created_at && (
                          <span className="text-[11px] text-slate-500 shrink-0">
                            {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      {/* Answer */}
                      <div className="ml-8 bg-slate-950/80 border border-slate-800/80 p-4 rounded-xl space-y-3">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap flex-1">
                            {item.answer}
                          </p>
                          <button
                            type="button"
                            onClick={() => handlePlayAnswerAudio(item)}
                            disabled={loadingTTSId === item.id}
                            className={`shrink-0 text-xs px-2.5 py-1.5 rounded-lg border flex items-center gap-1.5 transition-all cursor-pointer ${
                              playingAnswerId === item.id
                                ? 'bg-violet-600 border-violet-500 text-white shadow-md shadow-violet-600/30'
                                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
                            }`}
                            title="Listen to AI voice read-aloud"
                          >
                            {loadingTTSId === item.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" />
                            ) : playingAnswerId === item.id ? (
                              <>
                                <Square className="w-3.5 h-3.5 fill-current" />
                                <span>Stop</span>
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-3.5 h-3.5 text-violet-400" />
                                <span>Listen</span>
                              </>
                            )}
                          </button>
                        </div>

                        {/* Citations */}
                        {item.citations && item.citations.length > 0 && (
                          <div className="border-t border-slate-800/60 pt-2.5 flex flex-wrap items-center gap-2">
                            <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              Sources:
                            </span>
                            {item.citations.map((c, i) => (
                              <span
                                key={i}
                                className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700/60 font-mono"
                              >
                                {c.source || 'Document'} {c.page ? `(p. ${c.page})` : ''} {c.section ? `[${c.section}]` : ''}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: UPLOADED DOCUMENTS MANAGEMENT */}
        {activeTab === 'files' && (
          <div className="space-y-6">
            {/* Upload Box (Admin & Club Head Only) */}
            {canUpload ? (
              <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl space-y-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Upload className="w-4 h-4 text-indigo-400" />
                  Upload Club Document
                </h3>
                <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="md:col-span-2">
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.md"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="w-full text-sm text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600/20 file:text-indigo-300 hover:file:bg-indigo-600/30 file:cursor-pointer cursor-pointer border border-slate-800 bg-slate-950 p-1.5 rounded-xl"
                    />
                  </div>
                  <div className="flex gap-2">
                    <select
                      value={uploadCategory}
                      onChange={(e) => setUploadCategory(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="POST_MORTEM">Post-Mortem</option>
                      <option value="BUDGET">Budget / Finance</option>
                      <option value="VENUE_RULES">Venue Policy</option>
                      <option value="SPONSOR_DECK">Sponsorship</option>
                      <option value="MEETING_NOTES">Meeting Notes</option>
                      <option value="OTHER">Other</option>
                    </select>
                    <button
                      type="submit"
                      disabled={isUploading || !uploadFile}
                      className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-md shrink-0"
                    >
                      {isUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                      Upload
                    </button>
                  </div>
                </form>
                {uploadError && <p className="text-xs text-red-400">{uploadError}</p>}
              </div>
            ) : (
              <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl shadow-xl flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                    <Lock className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      Document Upload Restricted
                      <span className="text-[10px] uppercase font-semibold bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full border border-amber-500/20">
                        System Admin Only
                      </span>
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Only System Administrators can upload and add reference documents into the RAG knowledge brain.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Document List */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div className="relative w-72">
                  <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && fetchDocuments()}
                    placeholder="Search documents..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <span className="text-xs text-slate-400 font-medium">
                  {documents.length} document(s) in vector store
                </span>
              </div>

              {loadingDocs ? (
                <div className="p-8 text-center text-slate-400">Loading documents...</div>
              ) : documents.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No documents found. Upload meeting notes or post-mortems to power the RAG brain.
                </div>
              ) : (
                <div className="divide-y divide-slate-800">
                  {documents.map((doc) => (
                    <div key={doc.id} className="p-4 flex items-center justify-between hover:bg-slate-800/40 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                          <FileText className="w-4 h-4 text-indigo-400" />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-white">{doc.name || doc.filename}</h4>
                          <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                            <span className="uppercase text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-medium">
                              {doc.category}
                            </span>
                            <span>•</span>
                            <span>{doc.chunk_count} chunk(s)</span>
                            <span>•</span>
                            <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                          </div>
                        </div>
                      </div>
                      {canUpload && (
                        <button
                          onClick={() => handleDeleteDoc(doc.id)}
                          className="text-slate-500 hover:text-red-400 p-2 rounded-lg hover:bg-slate-800 transition-colors"
                          title="Delete document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Multilingual Voice Assistant Modal for RAG */}
      <VoiceAssistant
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        mode="rag"
        onTurnComplete={() => fetchRAGHistory()}
      />
    </DashboardLayout>
  );
}
