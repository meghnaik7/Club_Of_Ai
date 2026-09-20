import api from '../lib/axios';

export interface TranscriptionResponse {
  text: string;
  language: string;
  confidence?: number | null;
  request_id?: string;
}
export const TranscriptionResponse = {} as any;

export interface TTSRequest {
  text: string;
  language?: string;
  voice?: string;
  pace?: number;
}
export const TTSRequest = {} as any;

export interface TTSResponse {
  audio_base64: string;
  content_type: string;
  language: string;
  voice: string;
  duration_seconds?: number | null;
}
export const TTSResponse = {} as any;

export interface VoiceChatResponse {
  transcript: string;
  response_text: string;
  language: string;
  audio_base64?: string;
  audio_url?: string;
  thread_id?: string;
  proposals?: number[];
  status: string;
  details?: Record<string, any>;
  confidence?: number | null;
}
export const VoiceChatResponse = {} as any;

export interface LanguageListResponse {
  languages: Record<string, string>;
  default_language: string;
}
export const LanguageListResponse = {} as any;



export interface VoiceRAGResponse {
  transcript: string;
  answer: string;
  language: string;
  confidence: number;
  citations: Array<{
    source?: string;
    document_id?: string;
    filename?: string;
    category?: string;
    page?: number;
    section?: string;
    chunk_index?: number;
    snippet?: string;
    relevance_score?: number;
  }>;
  audio_base64?: string;
  content_type?: string;
  status: string;
}
export const VoiceRAGResponse = {} as any;


const VoiceService = {
  getLanguages: async (): Promise<LanguageListResponse> => {
    const res = await api.get<LanguageListResponse>('/voice/languages');
    return res.data;
  },

  transcribe: async (
    audioBlob: Blob,
    language?: string,
    filename: string = 'recording.wav'
  ): Promise<TranscriptionResponse> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, filename);
    if (language && language !== 'auto') {
      formData.append('language', language);
    }

    const res = await api.post<TranscriptionResponse>('/voice/transcribe', formData);
    return res.data;
  },

  synthesize: async (params: TTSRequest): Promise<TTSResponse> => {
    const res = await api.post<TTSResponse>('/voice/synthesize', params);
    return res.data;
  },

  voiceChat: async (
    audioBlob: Blob,
    options?: {
      threadId?: string;
      eventId?: number;
      language?: string;
      voice?: string;
      filename?: string;
    }
  ): Promise<VoiceChatResponse> => {
    const formData = new FormData();
    const fname = options?.filename || (audioBlob.type.includes('webm') ? 'recording.webm' : 'recording.wav');
    formData.append('audio', audioBlob, fname);

    if (options?.threadId) {
      formData.append('thread_id', options.threadId);
    }
    if (options?.eventId !== undefined && options?.eventId !== null) {
      formData.append('event_id', String(options.eventId));
    }
    if (options?.language && options.language !== 'auto') {
      formData.append('language', options.language);
    }
    if (options?.voice) {
      formData.append('voice', options.voice);
    }

    const res = await api.post<VoiceChatResponse>('/voice/chat', formData);
    return res.data;
  },


  voiceRAGQuery: async (
    audioBlob: Blob,
    options?: {
      eventId?: number;
      category?: string;
      language?: string;
      voice?: string;
      filename?: string;
    }
  ): Promise<VoiceRAGResponse> => {
    const formData = new FormData();
    const fname = options?.filename || (audioBlob.type.includes('webm') ? 'recording.webm' : 'recording.wav');
    formData.append('audio', audioBlob, fname);

    if (options?.eventId !== undefined && options?.eventId !== null) {
      formData.append('event_id', String(options.eventId));
    }
    if (options?.category) {
      formData.append('category', options.category);
    }
    if (options?.language && options.language !== 'auto') {
      formData.append('language', options.language);
    }
    if (options?.voice) {
      formData.append('voice', options.voice);
    }

    const res = await api.post<VoiceRAGResponse>('/voice/rag-query', formData);
    return res.data;
  },

};

export default VoiceService;
