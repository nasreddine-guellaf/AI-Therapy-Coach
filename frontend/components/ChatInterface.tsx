"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  deleteConversation,
  getConversation,
  listConversations,
  sendMessage,
} from "@/services/apiClient";
import type {
  ConversationMessage,
  ConversationSummary,
} from "@/types/conversation";

import { ConversationHistoryPanel } from "./ConversationHistoryPanel";
import { MessageBubble } from "./MessageBubble";
import { VoiceRecorder } from "./VoiceRecorder";

const MAX_MESSAGE_LENGTH = 5_000;

function createMessage(
  role: ConversationMessage["role"],
  content: string,
): ConversationMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
  };
}

export function ChatInterface() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refreshHistory = useCallback(async (signal?: AbortSignal) => {
    try {
      const history = await listConversations(signal);
      setConversations(history);
      setHistoryError(null);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") {
        return;
      }
      setHistoryError("Conversation history could not be loaded.");
    } finally {
      if (!signal?.aborted) setIsHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshHistory(controller.signal);
    return () => controller.abort();
  }, [refreshHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, error]);

  async function submitMessage(message: string) {
    const normalizedMessage = message.trim();
    if (!normalizedMessage || isLoading) return;

    setMessages((current) => [
      ...current,
      createMessage("user", normalizedMessage),
    ]);
    setDraft("");
    setError(null);
    setLastFailedMessage(null);
    setIsLoading(true);

    try {
      const response = await sendMessage({
        message: normalizedMessage,
        session_id: sessionId,
      });
      if (response.session_id) {
        setSessionId(response.session_id);
        void refreshHistory();
      }
      setMessages((current) => [
        ...current,
        createMessage("assistant", response.message),
      ]);
    } catch (requestError) {
      const messageText =
        requestError instanceof ApiError
          ? requestError.message
          : "Something went wrong. Please try again.";
      setError(messageText);
      setLastFailedMessage(normalizedMessage);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(draft);
  }

  function startNewConversation() {
    if (isLoading) return;
    setSessionId(undefined);
    setMessages([]);
    setDraft("");
    setError(null);
    setLastFailedMessage(null);
  }

  async function openConversation(selectedSessionId: string) {
    if (isLoading) return;
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      const conversation = await getConversation(selectedSessionId);
      setSessionId(conversation.session_id);
      setMessages(
        conversation.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          createdAt: message.created_at,
        })),
      );
      setError(null);
      setLastFailedMessage(null);
    } catch {
      setHistoryError("This conversation could not be opened.");
    } finally {
      setIsHistoryLoading(false);
    }
  }

  async function removeConversation(selectedSessionId: string) {
    if (isLoading || !window.confirm("Delete this conversation permanently?")) {
      return;
    }
    setHistoryError(null);
    try {
      await deleteConversation(selectedSessionId);
      setConversations((current) =>
        current.filter((item) => item.session_id !== selectedSessionId),
      );
      if (sessionId === selectedSessionId) startNewConversation();
    } catch {
      setHistoryError("This conversation could not be deleted.");
    }
  }

  return (
    <div className="conversation-workspace">
      <ConversationHistoryPanel
        conversations={conversations}
        activeSessionId={sessionId}
        isLoading={isHistoryLoading}
        error={historyError}
        disabled={isLoading || isHistoryLoading}
        onOpen={(selectedSessionId) => void openConversation(selectedSessionId)}
        onDelete={(selectedSessionId) => void removeConversation(selectedSessionId)}
      />
      <section className="chat-card" aria-labelledby="conversation-title">
      <header className="chat-header">
        <div>
          <span className="eyebrow">Private reflection</span>
          <h2 id="conversation-title">Conversation</h2>
        </div>
        <div className="chat-header-actions">
          <span className="session-badge">
            {sessionId ? "Active session" : "New session"}
          </span>
          <button
            className="new-conversation-button"
            type="button"
            onClick={startNewConversation}
            disabled={isLoading || (!sessionId && messages.length === 0)}
          >
            New conversation
          </button>
        </div>
      </header>

      <div
        className="message-list"
        aria-live="polite"
        aria-busy={isLoading}
      >
        {messages.length === 0 && !isLoading ? (
          <div className="empty-state">
            <div className="empty-state-icon" aria-hidden="true">
              ✦
            </div>
            <h3>What would you like to reflect on?</h3>
            <p>
              Share what is on your mind. The coach can help you organize your
              thoughts and consider constructive next steps.
            </p>
            <div className="prompt-suggestions" aria-label="Prompt suggestions">
              {["I feel overwhelmed", "Help me set a small goal"].map(
                (suggestion) => (
                  <button
                    type="button"
                    key={suggestion}
                    onClick={() => setDraft(suggestion)}
                  >
                    {suggestion}
                  </button>
                ),
              )}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {isLoading && (
          <div className="message-row message-row--assistant" role="status">
            <div className="message-avatar" aria-hidden="true">
              AI
            </div>
            <div className="typing-indicator" aria-label="Coach is responding">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        {error && (
          <div className="error-state" role="alert">
            <div>
              <strong>Message not delivered</strong>
              <p>{error}</p>
            </div>
            {lastFailedMessage && (
              <button
                type="button"
                onClick={() => void submitMessage(lastFailedMessage)}
              >
                Try again
              </button>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="message-input">
          Your message
        </label>
        <textarea
          id="message-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Write what is on your mind..."
          rows={1}
          maxLength={MAX_MESSAGE_LENGTH}
          disabled={isLoading}
        />
        <VoiceRecorder />
        <button
          className="send-button"
          type="submit"
          disabled={isLoading || !draft.trim()}
          aria-label="Send message"
        >
          <span>Send</span>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m5 12 14-7-4 14-3-6-7-1Z" />
          </svg>
        </button>
        <div className="composer-note">
          AI can make mistakes. Do not use this service for emergencies or
          medical decisions.
        </div>
      </form>
      </section>
    </div>
  );
}
