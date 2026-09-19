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
};

export default AIService;
