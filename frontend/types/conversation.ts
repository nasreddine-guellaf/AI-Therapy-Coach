export type MessageRole = "user" | "assistant" | "system";

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
}

export interface ConversationResponse { message: string; status: string }
