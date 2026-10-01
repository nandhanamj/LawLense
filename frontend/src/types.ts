/**
 * Type definitions for the LawLens legal assistant frontend.
 * Accurately models the Django REST API contracts and frontend state.
 */

export interface Citation {
  act: string;
  section: string;
  title?: string | null;
  supporting_text?: string | null;
  evidence?: string | null;
  source?: string | null;
  source_info?: string | null;
}

export interface LegalResponse {
  query?: string | null;
  answer: string;
  supported: boolean;
  citations: Citation[];
  refusal_reason?: string | null;
  is_refusal: boolean;
  language?: string | null;
  session_id?: string;
  conversation_id?: string;
}

export interface ChatRequest {
  query: string;
  conversation_id?: string;
  session_id?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: LegalResponse;
  timestamp: Date;
  isError?: boolean;
}
