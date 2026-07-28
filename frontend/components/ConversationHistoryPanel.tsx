import type { ConversationSummary } from "@/types/conversation";


interface ConversationHistoryPanelProps {
  conversations: ConversationSummary[];
  activeSessionId?: string;
  isLoading: boolean;
  error: string | null;
  disabled: boolean;
  onOpen: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

const DATE_FORMATTER = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

export function ConversationHistoryPanel({
  conversations,
  activeSessionId,
  isLoading,
  error,
  disabled,
  onOpen,
  onDelete,
}: ConversationHistoryPanelProps) {
  return (
    <aside className="conversation-history" aria-label="Conversation history">
      <div className="history-heading">
        <span className="eyebrow">Your private history</span>
        <h3>Conversations</h3>
      </div>

      {isLoading ? <p className="history-status">Loading history…</p> : null}
      {error ? <p className="history-error">{error}</p> : null}
      {!isLoading && !error && conversations.length === 0 ? (
        <p className="history-status">Your saved conversations will appear here.</p>
      ) : null}

      <div className="history-list">
        {conversations.map((conversation) => {
          const isActive = conversation.session_id === activeSessionId;
          return (
            <article
              className={`history-item${isActive ? " history-item--active" : ""}`}
              key={conversation.session_id}
            >
              <button
                className="history-open-button"
                type="button"
                onClick={() => onOpen(conversation.session_id)}
                disabled={disabled}
                aria-current={isActive ? "page" : undefined}
              >
                <span>{conversation.title || "Untitled conversation"}</span>
                <small>
                  {conversation.last_message_preview || "No messages yet"}
                </small>
                <time dateTime={conversation.updated_at}>
                  {DATE_FORMATTER.format(new Date(conversation.updated_at))}
                </time>
              </button>
              <button
                className="history-delete-button"
                type="button"
                onClick={() => onDelete(conversation.session_id)}
                disabled={disabled}
                aria-label={`Delete ${conversation.title || "conversation"}`}
              >
                Delete
              </button>
            </article>
          );
        })}
      </div>
    </aside>
  );
}
