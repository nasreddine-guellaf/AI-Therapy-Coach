export type MessageRole = "user" | "assistant" | "system";

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface ConversationRequest {
  message: string;
  session_id?: string;
}

export interface ConversationResponse {
  message: string;
  status: string;
  session_id: string | null;
  memory_items_used: number;
  rag_chunks_used: number;
  source_ids: string[];
}

export interface ConversationSummary {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
}

export interface PersistedConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationDetail {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: PersistedConversationMessage[];
}
