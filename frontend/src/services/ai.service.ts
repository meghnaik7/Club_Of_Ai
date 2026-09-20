import api from '../lib/axios';

export type AICommandRequest = {
  command: string;
  active_event_id?: number;
  confirm_proposal_id?: number;
  auto_confirm?: boolean;
}

export type AICommandResponse = {
  response: string;
  proposals: number[];
  status: string;
  details?: Record<string, any>;
}

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  proposals?: number[];
  status?: string;
  details?: Record<string, any>;
}

export type AIFeedbackRequest = {
  proposal_id?: number;
  event_id?: number;
  rating: 'GOOD' | 'POOR' | string;
  feedback_type?: string;
  comment?: string;
  metadata_json?: Record<string, any>;
};

export type FeedbackOut = {
  id: number;
  proposal_id?: number;
  user_id?: number;
  event_id?: number;
  rating: string;
  feedback_type?: string;
  comment?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
};

export type FeedbackAnalytics = {
  total_feedbacks: number;
  positive_count: number;
  negative_count: number;
  satisfaction_rate_percent: number;
  proposal_acceptance_rate_percent: number;
  recovery_success_rate_percent: number;
  top_negative_reasons: Record<string, number>;
  recent_feedbacks: FeedbackOut[];
};

const AIService = {
  executeCommand: (data: AICommandRequest) =>
    api.post<AICommandResponse>('/ai/', data).then(r => r.data),

  confirmProposal: (proposal_id: number, active_event_id?: number) =>
    api.post<AICommandResponse>('/ai/', {
      command: `confirm proposal ${proposal_id}`,
      confirm_proposal_id: proposal_id,
      active_event_id,
      auto_confirm: true,
    }).then(r => r.data),

  rejectProposal: (proposal_id: number, active_event_id?: number) =>
    api.post<AICommandResponse>('/ai/', {
      command: `reject proposal ${proposal_id}`,
      active_event_id,
    }).then(r => r.data),

  submitFeedback: (data: AIFeedbackRequest) =>
    api.post<FeedbackOut>('/ai/feedback', data).then(r => r.data),

  getFeedbackAnalytics: (eventId?: number) =>
    api.get<FeedbackAnalytics>('/ai/feedback/analytics', {
      params: eventId ? { event_id: eventId } : {}
    }).then(r => r.data),

  getRecentFeedbacks: (eventId?: number, limit: number = 20) =>
    api.get<FeedbackOut[]>('/ai/feedback', {
      params: { ...(eventId ? { event_id: eventId } : {}), limit }
    }).then(r => r.data),

  getHistory: (active_event_id?: number) =>
    api.get<{
      items: Array<{
        id: string;
        question: string;
        answer: string;
        citations?: any[];
        status?: string;
        proposals?: number[];
        created_at?: string;
      }>;
      total: number;
    }>('/ai/history', {
      params: active_event_id ? { active_event_id } : {}
    }).then(r => r.data),

  clearHistory: (active_event_id?: number) =>
    api.delete('/ai/history', {
      params: active_event_id ? { active_event_id } : {}
    }).then(r => r.data),
};

export default AIService;


