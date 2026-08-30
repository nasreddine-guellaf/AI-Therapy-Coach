import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

import type { ConversationMessage } from "@/types/conversation";
import {
  deduplicateSources,
  formatSourceLabel,
} from "@/utils/sourcePresentation";

interface MessageBubbleProps {
  message: ConversationMessage;
}

const REMARK_PLUGINS = [remarkBreaks];
const SAFE_MARKDOWN_ELEMENTS = [
  "p",
  "strong",
  "em",
  "ul",
  "ol",
  "li",
  "br",
];

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const label = isUser ? "You" : "Coach";
  const time = new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(message.createdAt));
  const sources = deduplicateSources(message.sources ?? []);
  const showSourceIds = process.env.NEXT_PUBLIC_SHOW_SOURCE_IDS === "true";

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
        {isAssistant ? (
          <div className="assistant-markdown">
            <ReactMarkdown
              allowedElements={SAFE_MARKDOWN_ELEMENTS}
              remarkPlugins={REMARK_PLUGINS}
              skipHtml
              unwrapDisallowed
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <p>{message.content}</p>
        )}
        {!isUser && sources.length > 0 ? (
          <div className="message-sources" aria-label="Response sources">
            <strong>Sources</strong>
            <ul>
              {sources.map((source) => (
                <li key={`${source.filename}:${source.page_number ?? "none"}`}>
                  <span>{formatSourceLabel(source)}</span>
                  {showSourceIds ? <code>{source.source_id}</code> : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </article>
  );
}
