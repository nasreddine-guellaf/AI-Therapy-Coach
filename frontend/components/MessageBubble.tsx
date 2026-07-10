import type { ConversationMessage } from "@/types/conversation";

export function MessageBubble({ message }: { message: ConversationMessage }) {
  return <article className={`message ${message.role}`} aria-label={`Message ${message.role}`}>{message.content}</article>;
}
