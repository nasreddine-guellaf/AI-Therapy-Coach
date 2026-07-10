"use client";
import { FormEvent, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { VoiceRecorder } from "./VoiceRecorder";
import type { ConversationMessage } from "@/types/conversation";

export function ChatInterface() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [draft, setDraft] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: "user", content: draft.trim() }]);
    setDraft(""); // TODO: call apiClient and append the validated assistant response.
  }
  return <section className="chat" aria-label="Conversation">
    <div className="messages">{messages.length ? messages.map((m) => <MessageBubble key={m.id} message={m} />) : <p>Comment souhaitez-vous être accompagné aujourd'hui ?</p>}</div>
    <form onSubmit={submit}><input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Écrivez votre message…" aria-label="Message" /><button>Envoyer</button><VoiceRecorder /></form>
  </section>;
}
