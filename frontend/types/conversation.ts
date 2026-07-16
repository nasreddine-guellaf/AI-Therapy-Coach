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
  memory_items_used: number;
  rag_chunks_used: number;
  source_ids: string[];
}
