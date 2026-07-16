import type { ConversationMessage } from "@/types/conversation";

interface MessageBubbleProps {
  message: ConversationMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const label = isUser ? "You" : "Coach";
  const time = new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(message.createdAt));

  return (
    <article className={`message-row message-row--${message.role}`}>
      {!isUser && (
        <div className="message-avatar" aria-hidden="true">
          AI
        </div>
      )}
      <div className={`message-bubble message-bubble--${message.role}`}>
        <div className="message-meta">
          <span>{label}</span>
          <time dateTime={message.createdAt}>{time}</time>
        </div>
        <p>{message.content}</p>
      </div>
    </article>
  );
}
